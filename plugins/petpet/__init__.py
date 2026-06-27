from arclet.alconna import Alconna, Args, CommandMeta
from arclet.entari import At, Image, Session, command, plugin, MessageChain, metadata

from core.event import NudgeEvent
from .generate import generate


metadata(
    name="摸头",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)


cmd = Alconna(
    "摸",
    Args["target", [At, str]],
    meta=CommandMeta("rua别人", example="$摸@123456", extra={"supports": {"mirai"}}),
)


disp = command.mount(cmd, skip_for_unmatch=False).as_execute()


@disp.handle()
async def rua(
    session: Session,
    target: At | str,
):

    if isinstance(target, At):
        if not target.id:
            return "无法获取目标QQ号"
        target_id = target.id
    else:
        target_id = target
    try:
        user = await session.account.user_get(target_id)
        if not user.avatar:
            return "无法获取目标头像"
        data = await session.account.download(user.avatar)
    except Exception:
        return "无法获取目标头像"
    img = generate(data).getvalue()
    return MessageChain(Image.of(raw=img))


@plugin.listen(NudgeEvent, label="头像双击响应")
async def on_nudge(event: NudgeEvent, session: Session):
    """双击别人头像来摸头"""
    if event.target_id != int(session.account.self_id):
        return
    try:
        user = await session.account.user_get(str(event.sender_id))
        if not user.avatar:
            return
        data = await session.account.download(user.avatar)
    except Exception:
        return

    img = generate(data).getvalue()
    await session.account.send_message(
        str(event.group_id),
        MessageChain(Image.of(raw=img)),
    )
