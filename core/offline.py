from arclet.entari import Entari, listen
from arclet.entari.config import EntariConfig
from arclet.entari.event.base import LoginUpdatedEvent
from satori import Login, LoginStatus, MessageObject, Text


@listen(LoginUpdatedEvent, priority=13)
async def report(login: Login, app: Entari, reason: MessageObject | None = None):
    # if isinstance(event.exception, NetworkError):
    #     args = event.exception.args
    #     if args[1]["code"] == 500 and "GROUP_CHAT_LIMITED" in args[1]["msg"]:
    #         return
    if login.status is LoginStatus.ONLINE:
        return
    superusers = EntariConfig.instance.basic.superusers

    accounts = [acc for acc in app.accounts.values() if acc.platform != login.platform and acc.platform in superusers]

    msg = f"登录状态更新：\n\n账号：[{login.platform}] {login.user.id}\n状态：{login.status.name}\n"
    if reason:
        msg += f"原因：{reason}\n"
    for account in accounts:
        channel = await account.user_channel_create(superusers[account.platform][0])
        await account.send_message(channel, [Text(msg)])
