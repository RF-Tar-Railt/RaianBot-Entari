from arclet.entari import Entari, listen
from arclet.entari.event.base import LoginUpdatedEvent
from arclet.entari.config import EntariConfig
from satori import Login, MessageObject, Text


@listen(LoginUpdatedEvent, priority=13)
async def report(login: Login, app: Entari, reason: MessageObject | None = None):
    # if isinstance(event.exception, NetworkError):
    #     args = event.exception.args
    #     if args[1]["code"] == 500 and "GROUP_CHAT_LIMITED" in args[1]["msg"]:
    #         return
    superusers = EntariConfig.instance.basic.superusers
    qqs = [int(acc) for plat in superusers for acc in superusers[plat] if plat in ("onebot", "milky")]
    accounts = [acc for acc in app.accounts.values() if acc.platform in ("onebot", "milky")]

    msg = f"登录状态更新：\n\n账号：[{login.platform}] {login.user.id}\n状态：{login.status.name}\n"
    if reason:
        msg += f"原因：{reason}\n"
    for account in accounts:
        async for friend in account.friend_list():
            if friend.user and int(friend.user.id) in qqs:
                await account.send_private_message(friend.user, [Text(msg)])
                break
