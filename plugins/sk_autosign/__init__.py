import asyncio
import re
from itertools import groupby
from operator import attrgetter
from datetime import datetime

from arclet.alconna import Alconna, Args, CommandMeta, Field, Option
from arclet.entari import scheduler, command, MessageChain, Entari, metadata
from entari_plugin_database import AsyncSession, select
from entari_plugin_database import service as db_service
from entari_plugin_user import UserSession
from satori import Image


from entari_plugin_browser import md2img
from tools.sk_autosign import bind, sign

from .model import SKAutoSignRecord, SKAutoSignResultRecord
from .utils import get_bind_by_user_id


metadata(
    name="森空岛自动签到",
    description="每天 0:30 开始自动签到，若与绑定者为好友则同时会私聊通知签到结果",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)


alc = Alconna(
    "森空岛签到",
    Option("绑定", Args["token", str, Field(unmatch_tips=lambda x: f"请输入你的凭据，而不是{x}")], compact=True),
    Option("解除", compact=True),
    Option("查询", Args["uid?", str, Field(unmatch_tips=lambda x: f"请输入角色uid，而不是{x}")], compact=True),
    Option("方法"),
    meta=CommandMeta(
        "森空岛方舟自动签到",
        usage="""\
每天 0:30 开始自动签到，若与绑定者为好友则同时会私聊通知签到结果

**token获取方法**：在森空岛官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.skland.com/account/info/hg

B服：https://web-api.skland.com/account/info/ak-b

***请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token***

再通过 ’渊白森空岛签到   绑定   你从网址里获取的token或者内容‘ 命令来绑定

**注意空格！！！**
""",
        example="""\
$森空岛签到方法
$绑定森空岛签到token1234
$森空岛签到绑定token1234
$解除森空岛签到
$森空岛签到结果
""",
        compact=True,
    ),
)
alc.shortcut("绑定森空岛签到", {"command": "森空岛签到 绑定", "prefix": True})
alc.shortcut("解除森空岛签到", {"command": "森空岛签到 解除", "prefix": True})
alc.shortcut("森空岛签到结果", {"command": "森空岛签到 查询", "prefix": True})
alc.shortcut(r"(\d+)森空岛签到结果", {"command": "森空岛签到 查询 {0}", "prefix": True})

disp = command.mount(alc, skip_for_unmatch=False).as_execute()


@disp.assign("$main")
async def signup(db_sess: AsyncSession, user_sess: UserSession):
    async with db_sess.begin():
        _record = await db_sess.get(SKAutoSignRecord, user_sess.user_id)
        if not _record:
            return "未绑定森空岛自动签到"
        ans = []
        async for resp in sign(_record):  # type: ignore
            res = SKAutoSignResultRecord(id=_record.id, uid=resp["target"], result=resp)
            await db_sess.merge(res)
            ans.append(resp["text"])
            await asyncio.sleep(1)
        if not ans:
            return "未进行签到，请等待"
        return "\n".join(ans)


@disp.assign("方法")
async def signup_method():
    text = """\
# 森空岛方舟自动签到

每天 0:30 开始自动签到，若与绑定者为好友则同时会私聊通知签到结果

**token获取方法**：在森空岛官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.skland.com/account/info/hg

B服：https://web-api.skland.com/account/info/ak-b

***请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token***

再通过 "渊白森空岛签到   绑定   你从网址里获取的token或者内容" 命令来绑定

**注意空格！！！**
"""
    img = await md2img(text)
    return MessageChain(Image.of(raw=img))


@disp.assign("绑定")
async def reg(token: command.Match[str], db_sess: AsyncSession, user_sess: UserSession):
    if "content" in token.result:
        mat = re.match('.*content(")?:(")?(?P<token>[^{}"]+).*', token.result)
        if not mat:
            return "输入格式有误！"
        token.result = mat["token"]
    try:
        await bind(token.result)
    except RuntimeError as e:
        return str(e)
    _record = SKAutoSignRecord(id=user_sess.user_id, token=token.result)
    await db_sess.merge(_record)
    await db_sess.commit()
    return "森空岛自动签到录入成功"


@disp.assign("解除")
async def rm(db_sess: AsyncSession, user_sess: UserSession):
    _record = await db_sess.get(SKAutoSignRecord, user_sess.user_id)
    if not _record:
        return "未绑定森空岛自动签到"
    for res in (
        await db_sess.scalars(select(SKAutoSignResultRecord).where(SKAutoSignResultRecord.id == _record.id))
    ).all():
        await db_sess.delete(res)
    await db_sess.delete(_record)
    await db_sess.commit()
    return "解除森空岛自动签到成功"


@disp.assign("查询")
async def check(uid: command.Match[str], db_sess: AsyncSession, user_sess: UserSession):
    _record = await db_sess.get(SKAutoSignRecord, user_sess.user_id)
    if not _record:
        return "未绑定森空岛自动签到"
    ans = []
    now = datetime.now()
    signed = now.replace(hour=0, minute=30, second=0, microsecond=0)
    if uid.available:
        for res in (
            await db_sess.scalars(
                select(SKAutoSignResultRecord)
                .where(SKAutoSignResultRecord.id == _record.id)
                .where(SKAutoSignResultRecord.uid == uid.result)
                .where(SKAutoSignResultRecord.date >= signed)
            )
        ).all():
            ans.append(res.result["text"])
    else:
        for res in (
            await db_sess.scalars(
                select(SKAutoSignResultRecord)
                .where(SKAutoSignResultRecord.id == _record.id)
                .where(SKAutoSignResultRecord.date >= signed)
            )
        ).all():
            ans.append(res.result["text"])
    if not ans:
        return "未进行签到，请等待"
    return "\n".join(ans)


@scheduler.cron("30 0 * * * 0", label="森空岛自动签到")
async def shed(app: Entari):
    """每日 0:30 自动签到"""
    results = {}

    async with db_service.get_session() as session:
        for rec in (await session.scalars(select(SKAutoSignRecord))).all():
            ans = results.setdefault(rec.id, [])
            async for resp in sign(rec):  # type: ignore
                if resp["status"]:
                    res = SKAutoSignResultRecord(id=rec.id, uid=resp["target"], result=resp)
                    await session.merge(res)
                    ans.append(resp["text"])
                await asyncio.sleep(1)
        await session.commit()
    accounts = list(app.accounts.values())
    accounts.sort(key=attrgetter("platform"))
    grouped = {k: list(g) for k, g in groupby(accounts, key=attrgetter("platform"))}
    for user_id, ans in results.items():
        if not ans:
            continue
        user_bind = await get_bind_by_user_id(user_id)
        if not user_bind:
            continue
        for account in grouped.get(user_bind.platform, []):
            try:
                await asyncio.sleep(1)
                channel = await account.user_channel_create(user_bind.platform_id)
                await account.send_message(channel, "\n".join(ans))
                break
            except Exception:
                continue
