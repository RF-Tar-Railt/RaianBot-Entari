from arclet.entari import Entari, Session, ChannelType, plugin
from arclet.entari.event.base import GuildAddedEvent, GuildRemovedEvent


@plugin.listen(GuildAddedEvent, label="入群公告")
async def on_guild_added(session: Session[GuildAddedEvent], app: Entari):
    """入群公告"""
    superusers = [
        acc
        for plat in app.config.basic.superusers
        for acc in app.config.basic.superusers[plat]
        if plat == session.account.platform
    ]
    if superusers:
        channel = await session.user_channel_create(superusers[0])
        await session.account.send_message(
            channel,
            f"收到加入群聊事件\n群聊: {session.event.guild}",
        )
    async for channel in session.channel_list():
        if channel.type is ChannelType.TEXT:
            await session.account.send_message(
                channel,
                f"我是机器人 {app.config.basic.nickname}\n"
                f"如果有需要可以联系主人 {superusers[0] if superusers else ''}，\n"
                f"尝试发送 {app.config.basic.prefix[0]}帮助 以查看功能列表\n"
                "项目地址：https://github.com/RF-Tar-Railt/RaianBot-Entari\n"
                "赞助（爱发电）：https://afdian.net/@rf_tar_railt\n"
                "机器人交流群：122680593",
            )


@plugin.listen(GuildRemovedEvent, label="退群公告")
async def on_guild_removed(session: Session[GuildRemovedEvent], app: Entari):
    """退群公告"""
    superusers = [
        acc
        for plat in app.config.basic.superusers
        for acc in app.config.basic.superusers[plat]
        if plat == session.account.platform
    ]
    if superusers:
        channel = await session.user_channel_create(superusers[0])
        await session.account.send_message(
            channel,
            f"收到退出群聊事件\n群聊: {session.event.guild}",
        )
