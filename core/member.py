from arclet.entari import ChannelType, Session, plugin, metadata
from arclet.entari.event.base import GuildMemberAddedEvent, GuildMemberRemovedEvent


metadata(
    name="用户入群/退群提醒",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
    version="0.1.0",
    description="核心功能中的用户入群/退群提醒",
)


@plugin.listen(GuildMemberRemovedEvent, label="member_leave")
async def on_member_leave(session: Session[GuildMemberRemovedEvent]):
    """用户离群提醒"""
    async for channel in session.channel_list():
        if channel.type is ChannelType.TEXT:
            await session.account.send_message(channel, f"可惜了！\n{session.event.user.id}退群了！")
            return


@plugin.listen(GuildMemberAddedEvent, label="member_join")
async def on_member_join(session: Session[GuildMemberAddedEvent]):
    """用户入群提醒"""
    async for channel in session.channel_list():
        if channel.type is ChannelType.TEXT:
            await session.account.send_message(channel, f"欢迎新成员！\n{session.event.user.id} 进群了就别想跑哦~")
            return
