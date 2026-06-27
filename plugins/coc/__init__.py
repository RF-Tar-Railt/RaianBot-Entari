import re
from contextlib import suppress

import diro
from arclet.alconna import Alconna, Args, CommandMeta, Field, Option, namespace
from arclet.alconna.tools import MarkdownTextFormatter
from arclet.entari import command, Session, metadata
from entari_plugin_database import AsyncSession
from nepattern import BasePattern, MatchMode
from satori import ChannelType
from sqlalchemy import select

from tools.dice import coc6, coc6d, coc7, coc7d, deck_list, dnd, draw, expr, long_insane, rd0, st, temp_insane
from tools.dice.constant import help_sc

from .model import CocRule

# fmt: off

metadata(
    name="骰娘功能",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)

with namespace("coc") as np:
    np.headers = [".", "。", "/"]
    np.formatter_type = MarkdownTextFormatter

    name_c = Alconna(
        "name",
        Args["key#名字格式", ["cn", "en", "jp", "enzh"], "$r"]["cnt#名字数量", int, 1],
        meta=CommandMeta(
            "随机名字",
            usage="主要为中文名，日文名和英文名",
            example=".name 5",
            compact=True,
        ),
    )
    name_disp = command.mount(name_c, use_config_prefix=False, skip_for_unmatch=False).as_execute()

    draw_c = Alconna(
        "draw",
        Args["key#牌堆名称", str, "调查员信息"]["cnt#抽牌数量", int, 1],
        Option("ls|list", help_text="查看牌堆列表"),
        meta=CommandMeta(
            "抽牌",
            usage="牌堆包括塔罗牌，调查员等",
            example=".draw 调查员信息 1",
            compact=True,
        ),
    )
    draw_disp = command.mount(draw_c, use_config_prefix=False, skip_for_unmatch=False).as_execute()

    ra_c = Alconna(
        "ra",
        Args["attr#属性名称，如name、名字、str、力量", str, "快速"]["exp", int, -1],
        meta=CommandMeta(
            "快速检定",
            usage="不传入 exp 则不进行结果检定",
            example=".ra str 80",
            compact=True,
        ),
    )
    ra_disp = command.mount(ra_c, use_config_prefix=False, skip_for_unmatch=False).as_execute()

    rd_c = Alconna(
        "r",
        Args["pattern#骰子表达式", "re:[^a]+", "1d100"]["exp#期望值", int, -1],
        meta=CommandMeta(
            "投掷指令",
            usage=(
                "d：骰子设定指令\n"
                "#：多轮投掷指令，#后接数字即可设定多轮投掷\n"
                "bp：奖励骰与惩罚骰\n"
            ),
            example=".r1d6",
            compact=True,
        ),
    )
    rd_disp = command.mount(rd_c, use_config_prefix=False, skip_for_unmatch=False).as_execute()

    s_or_f = BasePattern(r"\d+(?:d\d+)?\/\d+(?:d\d+)?", mode=MatchMode.REGEX_MATCH, alias="suc/fail")
    sc_c = Alconna(
        "sc",
        Args[
            "sf#惩罚值",
            s_or_f,
            Field(
                unmatch_tips=lambda x: "表达式格式错误，应为 '数字/数字' 或 '骰子表达式/骰子表达式'，比如 '1d10/1d100'",
                missing_tips=lambda: "需要判断表达式。可以尝试输入 '/sc 1d10/1d100'"
            )
        ],
        Args["san", int, 80],
        meta=CommandMeta(
            "疯狂检定",
            usage="success：判定成功降低san值，支持x或xdy语法\n"
            "failure：判定失败降低san值，支持语法如上\n"
            "san_number：当前san值，默认为 80",
            example=".sc 1d6/1d6 80",
        ),
    )
    sc_disp = command.mount(sc_c, use_config_prefix=False, skip_for_unmatch=False).as_execute()

    st_c = Alconna("st", meta=CommandMeta("射击命中判定", usage="自动掷骰1d20"))
    st_disp = command.mount(st_c, use_config_prefix=False).as_execute()
    ti_c = Alconna("ti", meta=CommandMeta("临时疯狂症状", usage="自动掷骰1d10"))
    ti_disp = command.mount(ti_c, use_config_prefix=False).as_execute()
    li_c = Alconna("li", meta=CommandMeta("总结疯狂症状", usage="自动掷骰1d10"))
    li_disp = command.mount(li_c, use_config_prefix=False).as_execute()
    dnd_c = Alconna(
        "dnd",
        Args["val#生成数量", int, 1],
        meta=CommandMeta(
            "龙与地下城(DND)人物作成",
            example=".dnd 5",
            compact=True,
        ),
    )
    dnd_disp = command.mount(dnd_c, use_config_prefix=False, skip_for_unmatch=False).as_execute()
    setcoc_c = Alconna(
        "setcoc",
        Args["rule?#coc版本", int],
        meta=CommandMeta(
            "设置房规；不传入参数则为查看当前房规",
            example=".setcoc 2",
            compact=True,
        ),
    )
    setcoc_disp = command.mount(setcoc_c, use_config_prefix=False, skip_for_unmatch=False)
    coc_c = Alconna(
        "coc",
        Args["mode", ["6", "7", "6d", "7d"], Field("7", unmatch_tips=lambda x: "coc后随模式只能为 6，7，6d 和 7d")],
        Args["val#生成数量", int, 1],
        meta=CommandMeta(
            "克苏鲁的呼唤(COC)人物作成, 默认生成7版人物卡",
            usage="接d为详细作成，一次只能作成一个",
            example=".coc6d",
            compact=True,
        ),
    )
    coc_disp = command.mount(coc_c, use_config_prefix=False, skip_for_unmatch=False).as_execute()


# fmt: on


@name_disp.handle()
async def name_handle(key: str, cnt: int):
    if key == "$r" or key.isdigit():
        return draw("随机姓名", cnt)
    return draw(f"随机姓名_{key}", cnt)


@draw_disp.assign("list")
async def draw_list_handle():
    return "牌堆列表：\n * " + "\n * ".join(deck_list())


@draw_disp.assign("$main", priority=17)
async def draw_main_handle(key: str, cnt: int):
    return draw(key, cnt)


@ra_disp.handle(priority=14)
async def ra_handle(attr: str, exp: int, db_sess: AsyncSession, sess: Session | None = None):
    if sess and sess.event.channel:
        async with db_sess.begin():
            coc_rule = (
                await db_sess.scalars(
                    select(CocRule)
                    .where(CocRule.platform == sess.account.platform)
                    .where(CocRule.channel_id == sess.channel.id)
                )
            ).one_or_none()
            rule = coc_rule.rule if coc_rule else 0
    else:
        rule = 0
    if attr.isdigit():
        name = "快速"
        anum = int(attr)
    else:
        name = attr
        anum = exp
        if mat := re.fullmatch(r".+?(\d+)", name):
            anum = int(mat[1])
            name = name[: -len(mat[1])]
        if anum < 0:
            return ra_disp.finish(rd0("1d100", None, rule), block=True)

    dices = diro.parse("1D100")
    return ra_disp.finish(f"{name}检定:\n{expr(dices, anum, rule)}", block=True)


@rd_disp
async def rd_handle(pattern: str, exp: int, db_sess: AsyncSession, sess: Session | None = None):
    """coc骰娘功能"""
    if sess and sess.event.channel:
        async with db_sess.begin():
            coc_rule = (
                await db_sess.scalars(
                    select(CocRule)
                    .where(CocRule.platform == sess.account.platform)
                    .where(CocRule.channel_id == sess.channel.id)
                )
            ).one_or_none()
            rule = coc_rule.rule if coc_rule else 0
    else:
        rule = 0
    num = exp
    pat = pattern
    if pat.startswith("h"):
        pat = pat[1:]
        if sess:
            friends = sess.account.friend_list()
            async for friend in friends:
                if friend.user and friend.user.id == sess.user.id:
                    try:
                        ans = rd0(pat, num if num >= 0 else None, rule)
                    except ValueError:
                        ans = "出错了！"
                    await sess.account.send_private_message(sess.user, ans)
                    return
    with suppress(ValueError):
        return rd_disp.finish(rd0(pat, num if num >= 0 else None, rule), block=True)
    return rd_disp.finish("出错了！", block=True)


@setcoc_disp
async def setcoc_handle(db_sess: AsyncSession, sess: Session, rule: command.Match[int]):
    if not sess.event.channel or sess.channel.type is ChannelType.DIRECT:
        await sess.send("该指令对私聊无效果")
        return
    if not rule.available:
        async with db_sess.begin():
            coc_rule = (
                await db_sess.scalars(
                    select(CocRule)
                    .where(CocRule.platform == sess.account.platform)
                    .where(CocRule.channel_id == sess.channel.id)
                )
            ).one_or_none()
            current_rule = coc_rule.rule if coc_rule else 0
        await sess.send(f"当前房规为 {current_rule}")
        return
    if rule.result > 6 or rule.result < 0:
        await sess.send("规则错误，规则只能为0-6")
        return
    async with db_sess.begin():
        coc_rule = CocRule(platform=sess.account.platform, channel_id=sess.channel.id, rule=rule.result)
        await db_sess.merge(coc_rule)
        await db_sess.commit()
    await sess.send("设置成功")
    return


@st_disp
async def st_handle():
    return st()


@ti_disp
async def ti_handle():
    return temp_insane()


@li_disp
async def li_handle():
    return long_insane()


@coc_disp
async def coc_handle(mode: str, val: int):
    if val < 1:
        return "次数不能小于1"
    if mode == "6d":
        return coc6d()
    if mode == "7d":
        return coc7d()
    if mode == "6":
        return coc6(min(val, 20))
    return coc7(min(val, 20))


@dnd_disp
async def dnd_handle(val: int):
    return dnd(min(max(val, 1), 20))


@sc_disp
async def sc_handle(sf: command.Match[str], san: command.Match[int]):
    try:
        s_and_f = sf.result.split("/")
        success = diro.parse(s_and_f[0])
        success.roll()
        success = success.calc()
        failure = diro.parse(s_and_f[1])
        failure.roll()
        failure = failure.calc()
        r = diro.Dice().roll()()
        s = f"San Check:{r}"
        down = success if r <= san.result else failure
        s += f"\n理智降低了{down}点"
        if down >= san.result:
            s += "\n该调查员陷入了永久性疯狂"
        elif down >= (san.result // 5):
            s += "\n该调查员陷入了不定性疯狂"
        elif down >= 5:
            s += "\n该调查员陷入了临时性疯狂"
        return s
    except (IndexError, KeyError, ValueError):
        return help_sc
