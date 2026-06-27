import asyncio

from arclet.entari.command import Match, Query
from satori import Image, Message, Text, Author
from arclet.alconna import Alconna, Arg, Field, Option, CommandMeta
from arclet.entari import MessageChain, keeping, plugin, command, Session, Entari, inject
from arclet.entari.logger import log
from arclet.entari.event.lifespan import Startup, Cleanup
from arclet.entari.scheduler import every
from entari_plugin_browser import playwright_api
from entari_plugin_database import AsyncSession, select
from entari_plugin_database import service as db_service
from satori.exception import ActionFailed

from .api import WeiboAPI, WeiboPost
from .config import Config
from .model import WeiboSubscribe

weibo_fetch = Alconna(
    "微博",
    Arg(
        "user;?#微博用户名称",
        str,
        Field(
            completion=lambda: "比如说, 育碧", unmatch_tips=lambda x: f"请输入微博用户名称，而不是{x}\n例如: /微博 育碧"
        ),
    ),  # noqa: E501
    Arg("choice#选择第几个用户", int, Field(default=0, unmatch_tips=lambda x: f"请输入数字，而不是{x}")),
    Option(
        "动态",
        Arg("index?#从最前动态排起的第几个动态", int, Field(unmatch_tips=lambda x: f"请输入数字，而不是{x}"))
        + Arg("page?#第几页动态", int, Field(unmatch_tips=lambda x: f"请输入数字，而不是{x}")),
        dest="post",
        help_text="从微博获取指定用户的动态",
    ),
    Option("关注|增加关注", dest="follow", help_text="增加一位微博动态关注对象"),
    Option("取消关注|解除关注", dest="unfollow", help_text="解除一位微博动态关注对象"),
    Option("列出", dest="list", help_text="列出该群的微博动态关注对象"),
    meta=CommandMeta(
        "获取指定用户的微博资料",
        example="$微博 育碧\n$微博 育碧 动态 1\n$微博 育碧 关注\n$微博 育碧 取消关注",
    ),
)

_conf = plugin.plugin_config(Config)
api = keeping("weibo_api", WeiboAPI(_conf.user_agent, _conf.cookie))
logger = log.wrapper("[Weibo]")


@plugin.listen(Startup)
@inject("database/sqlalchemy")
async def _startup_weibo_api():
    await api.load()
    logger.info("微博用户数据加载完毕")


@plugin.listen(Cleanup)
async def _cleanup_weibo_api():
    await api.close()


async def _handle_post(data: WeiboPost):
    imgs: list[Image] = []

    async with playwright_api.page(viewport={"width": 800, "height": 2400}) as page:
        try:
            await page.click("html")
            await page.goto(data.url, timeout=20000, wait_until="networkidle")
            elem = page.locator(
                "//div[@class='card-wrap']", has=page.locator("//header[@class='weibo-top m-box']")
            ).first
            elem1 = page.locator("//article[@class='weibo-main']").first
            bounding = await elem.bounding_box()
            bounding1 = await elem1.bounding_box()
            assert bounding
            assert bounding1
            bounding["height"] += bounding1["height"]
            imgs.append(Image.of(raw=await page.screenshot(full_page=True, clip=bounding)))
        except Exception as e:
            logger.error(f"动态截图失败: {e}")

    for url in data.img_urls:
        async with api.session.get(url) as resp:
            # if url_imgs and bot.config.platform.tencentcloud:
            #     url = await bot.upload_to_cos(await resp.read(), f"weibo_dym_{token_hex(16)}.png")
            #     imgs.append(Picture(UrlResource(url)))
            # else:
            imgs.append(Image.of(raw=await resp.read()))
    return data.text or "表情", imgs


async def _handle_post_forward(data: WeiboPost, uid: str, name: str, avatar: str | None):
    first, imgs = await _handle_post(data)
    nodes = [MessageChain([first]), MessageChain(imgs)] if imgs else [MessageChain([first])]
    if data.video_url:
        nodes.append(MessageChain(f"视频链接: {data.video_url}"))  # type: ignore
    return Message(forward=True)(*[Message(content=[Author(uid, name, avatar), *i]) for i in nodes])


cmd = command.mount(weibo_fetch).as_execute()


@cmd.assign("$main")
async def wget(session: Session, user: Match[str], choice: Match[int]):
    if not user.available or not user.result:
        return "请指定微博用户名\n例如: /微博 育碧"
    _index = choice.result
    count = -1
    try:
        profiles = await api.get_profiles(user.result)
        count = len(profiles)
    except Exception as e:
        logger.error(f"WEIBO GET: {e} {type(e)}")
        return f"获取用户信息发生错误: {e!r}"
    if count <= 0:
        return "获取失败啦"
    if count == 1 or 0 <= _index < count:
        prof = profiles[_index]
    else:
        await session.send_message("查找到多名用户，请选择其中一位，限时 15秒")
        ans = await session.prompt(
            "\n".join(
                f"{str(index).rjust(len(str(count)), '0')}. {slot.name} - {slot.description.replace('.', '. ')}"
                for index, slot in enumerate(profiles)
            ),
            timeout=15,
        )
        if ans is None:
            return
        res = ans.extract_plain_text()
        if res and res.isdigit():
            _index = max(int(res), 0)
        if _index >= count:
            return "别捣乱！"
        prof = profiles[max(_index, 0)]
    try:
        async with api.session.get(prof.avatar) as resp:
            pic = Image.of(raw=await resp.read())
        return MessageChain(
            [
                pic,
                Text(
                    f"用户名: {prof.name} ({prof.id})\n"
                    f"介绍: {prof.description.replace('.', '. ')}\n"
                    f"动态数: {prof.statuses}\n"
                    f"是否可见: {'是' if prof.visitable else '否'}"
                ),
            ]
        )
    except ActionFailed:
        return f"""\
用户名: {prof.name}
介绍: {prof.description.replace(".", ". ")}
动态数: {prof.statuses}
是否可见: {"是" if prof.visitable else "否"}
"""


@cmd.assign("post")
async def wfetch(
    user: Match[str],
    choice: Match[int],
    index: Query[int] = Query("post.index", -1),
    page: Query[int] = Query("post.page", 1),
):
    try:
        if user.result.isdigit():
            prof = await api.get_profile(int(user.result), save=True, cache=True)
        else:
            prof = await api.get_profile_by_name(user.result, index=choice.result, save=True, cache=True)
        dynamic = await api.get_dynamic(prof, index=index.result, page=page.result)
    except Exception as e:
        logger.error(f"WEIBO FETCH: {e} {type(e)}")
        return f"获取动态发生错误: {e!r}"

    nodes = await _handle_post(dynamic)
    return MessageChain([nodes[0], *nodes[1]])


@cmd.assign("follow")
async def wfollow(session: Session, user: Match[str], choice: Match[int], db_session: AsyncSession):
    try:
        if user.result.isdigit():
            follower = await api.get_profile(int(user.result), save=True, cache=True)
        else:
            follower = await api.get_profile_by_name(user.result, index=choice.result, save=True, cache=True)
    except Exception as e:
        logger.error(f"WEIBO FOLLOW: {e} {type(e)}")
        return f"获取用户信息发生错误: {e!r}"

    rec = await db_session.get(
        WeiboSubscribe, (session.account.self_id, session.account.platform, session.channel.id, int(follower.id))
    )
    if rec:
        return f"该群已关注 {follower.name}！请不要重复关注"
    db_session.add(
        WeiboSubscribe(
            login_id=session.account.self_id,
            platform=session.account.platform,
            channel_id=session.channel.id,
            wid=int(follower.id),
        )
    )
    await db_session.commit()
    return f"关注 {follower.name} 成功！"


@cmd.assign("unfollow")
async def wunfollow(session: Session, user: Match[str], choice: Match[int], db_session: AsyncSession):
    try:
        if user.result.isdigit():
            follower = await api.get_profile(int(user.result), save=True, cache=True)
        else:
            follower = await api.get_profile_by_name(user.result, index=choice.result, save=True, cache=True)
    except Exception as e:
        logger.error(f"WEIBO FOLLOW: {e} {type(e)}")
        return f"获取用户信息发生错误: {e!r}"

    rec = await db_session.get(
        WeiboSubscribe, (session.account.self_id, session.account.platform, session.channel.id, int(follower.id))
    )
    if not rec:
        return f"该群未关注 {follower.name}！"
    await db_session.delete(rec)
    await db_session.commit()
    return f"解除关注 {follower.name} 成功！"


@cmd.assign("list")
async def wlist(session: Session, db_session: AsyncSession):
    recs = await db_session.scalars(
        select(WeiboSubscribe)
        .where(WeiboSubscribe.login_id == session.account.self_id)
        .where(WeiboSubscribe.platform == session.account.platform)
        .where(WeiboSubscribe.channel_id == session.channel.id)
    )
    recs = recs.all()
    if not recs:
        return "该群没有关注任何微博动态哦！"
    names = []
    for rec in recs:
        try:
            prof = await api.get_profile(rec.wid, save=False, cache=True)
            names.append(f"{prof.name} ({prof.id})")
        except Exception as e:
            logger.error(f"WEIBO GET PROFILE: {e} {type(e)}")
            names.append(str(rec.wid))
    return "该群关注的微博动态有:\n" + "\n".join(names)


FIRST_STARTUP = plugin.keeping("FIRST_STARTUP", {"updated": False})


@every(5, "minute", label="微博动态推送")
async def update(app: Entari):
    posts = {}  # wid -> WeiboDynamic | (Message, str)
    followers = {}  # dict[wid, dict[(login_id, platform), list[channel_id]]]
    mapping = {}
    async with db_service.get_session() as session:
        subscribers = (await session.scalars(select(WeiboSubscribe))).all()
        for follower in subscribers:
            channels = followers.setdefault(follower.wid, {}).setdefault((follower.login_id, follower.platform), [])
            channels.append(follower.channel_id)
    for uid in followers:
        wp = await api.get_profile(int(uid))
        wp = wp.copy()
        try:
            if res := await api.update(int(uid)):
                posts[int(uid)] = res
            else:
                continue
        except Exception as e:
            logger.error(f"WEIBO UPDATE: {e} {type(e)}")
            await api.cache.merge(wp)
            continue
    if not FIRST_STARTUP["updated"]:
        FIRST_STARTUP["updated"] = True
        posts.clear()
        mapping.clear()
        followers.clear()
        return

    accounts = {
        (account.self_id, account.platform): account for account in app.accounts.values() if account.platform != "qq"
    }
    for wid in followers:
        if wid not in posts:
            continue
        for login_info, channel_ids in followers[wid].items():
            if login_info not in accounts:
                continue
            acc = accounts[login_info]
            for channel_id in channel_ids:
                slot = posts[wid]
                if isinstance(slot, WeiboPost):
                    name = slot.user.name if slot.user else f"微博用户{wid}"
                    if _conf.forward_post:
                        if isinstance(_conf.forward_post, bool):
                            post = await _handle_post_forward(
                                slot, acc.self_id, name, slot.user.avatar if slot.user else None
                            )  # type: ignore
                        elif _conf.forward_post.get(acc.platform, False):
                            post = await _handle_post_forward(
                                slot, acc.self_id, name, slot.user.avatar if slot.user else None
                            )  # type: ignore
                        else:
                            post, _ = await _handle_post(slot)
                    else:
                        post, _ = await _handle_post(slot)
                    posts[wid] = (post, name)
                else:
                    post, name = slot  # type: ignore
                await acc.send_message(channel_id, f"{name} 有一条新动态！请查收!")
                await acc.send_message(channel_id, [post])
                await asyncio.sleep(10)

    posts.clear()
    mapping.clear()
    followers.clear()
