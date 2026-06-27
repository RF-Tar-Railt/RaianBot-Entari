from arclet.alconna import Alconna, Args, CommandMeta, Field
from arclet.entari import At, User, Image, Member, Session, command, MessageChain, metadata
from arknights_toolkit.random_operator import RandomOperator

from entari_plugin_browser import text2img


metadata(
    name="随机干员信息",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
    description="根据名字随机生成一个干员信息",
)


cmd = Alconna(
    "测试干员",
    Args[
        "name?#你的代号",
        [str, At],
        Field(completion=lambda: "你的代号是?", unmatch_tips=lambda x: f"输入的应该是名字或者 @提及某人，而不是 {x}"),  # noqa: E501
    ],
    meta=CommandMeta(
        "依据名字测试你会是什么干员",
        example="$测试干员 海猫",
    ),
)

ro_disp = command.mount(cmd, skip_for_unmatch=False).as_execute()


@ro_disp
async def ro(sess: Session, name: command.Match[At | str], user: User, member: Member | None = None):
    """依据名字随机生成干员"""
    gen = RandomOperator()
    if name.available:
        _name = name.result
        if isinstance(_name, str):
            text = gen.generate(_name)
        else:
            if _name.name:
                text = gen.generate(_name.name)
            elif sess.event.guild:
                target = await sess.account.guild_member_get(sess.event.guild.id, str(_name.id))
                text = gen.generate(target.nick or getattr(target.user, "name", str(_name.id)))
            else:
                target = await sess.account.user_get(str(_name.id))
                text = gen.generate(target.name or str(_name.id))
    else:
        text = gen.generate(getattr(member, "nick", None) or user.name or user.id)

    data = await text2img(text)
    return MessageChain(Image.of(raw=data))
