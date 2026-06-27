import re
from datetime import datetime

from arclet.entari import MessageCreatedEvent, Session, plugin, metadata

metadata(
    name="问候",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
)


pat = re.compile("^(早上好|早安|中午好|下午好|晚上好).*?")
pat1 = re.compile(".*?(早上好|早安|中午好|下午好|晚上好)$")


# @listen(MessageReceived)
# @record("greet")
# @exclusive
# @accessable

disp = plugin.dispatch(MessageCreatedEvent)


@disp.handle(priority=7)
async def greet(session: Session):
    """简单的问好"""
    content = session.content
    now = datetime.now()
    if pat.fullmatch(content) or pat1.fullmatch(content):
        if 6 <= now.hour < 11:
            reply = "\tο(=•ω＜=)ρ⌒☆\n早上好~"
        elif 11 <= now.hour < 13:
            reply = "\t(o゜▽゜)o☆\n中午好~"
        elif 13 <= now.hour < 18:
            reply = "\t（＾∀＾●）ﾉｼ\n下午好~"
        elif 18 <= now.hour < 24:
            reply = "\tヾ(≧ ▽ ≦)ゝ\n晚上好~"
        else:
            reply = "\t≧ ﹏ ≦\n时候不早了，睡觉吧"
        return await session.send(reply, reply_to=True)

    if content.startswith("晚安") or content.endswith("晚安"):
        if 0 <= now.hour < 6:
            reply = "\t时候不早了，睡觉吧~(￣o￣) . z Z"
        elif 20 < now.hour < 24:
            reply = "\t快睡觉~(￣▽￣)"
        else:
            reply = "\t喂，现在可不是休息的时候╰（‵□′）╯"
        return await session.send(reply, reply_to=True)
