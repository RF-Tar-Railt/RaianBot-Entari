from arclet.entari import Entari, Session, plugin
from arclet.entari.event.base import MessageCreatedEvent, FriendRequestEvent, GuildRequestEvent
from arclet.letoderea import step_out


@plugin.listen(FriendRequestEvent, label="好友请求事件")
async def on_friend_request(event: FriendRequestEvent, session: Session, app: Entari):
    """处理好友请求事件"""
    superusers = [
        acc
        for plat in app.config.basic.superusers
        for acc in app.config.basic.superusers[plat]
        if plat == session.account.platform
    ]
    if superusers:
        channel = await session.user_channel_create(superusers[0])
        await session.account.protocol.send_message(channel, f"收到添加好友请求：\n{event.user}")

        async def waiter(sess: Session[MessageCreatedEvent]):
            if sess.event.channel.id == channel.id:
                return sess.content

        await session.account.protocol.send_message(channel, "处理请求等待中")
        step = step_out(MessageCreatedEvent, waiter, block=True)
        resp = await step.wait(timeout=120)
        if not resp:
            await session.request_approve(False, "管理员超时未回复，请尝试重新发送请求")
            await session.account.protocol.send_message(channel, "处理请求超时")
            return
        if resp in ("同意", "yes", "y", "ok", "好", "是", "同意请求"):
            await session.request_approve(True)
            await session.account.protocol.send_message(channel, "已同意好友请求")
            return
        await session.request_approve(False, "管理员拒绝了请求")
        await session.account.protocol.send_message(channel, "已拒绝好友请求")


@plugin.listen(GuildRequestEvent, label="入群请求事件")
async def on_guild_request(event: GuildRequestEvent, session: Session, app: Entari):
    """处理入群请求事件"""
    superusers = [
        acc
        for plat in app.config.basic.superusers
        for acc in app.config.basic.superusers[plat]
        if plat == session.account.platform
    ]
    if superusers:
        channel_send = await session.user_channel_create(superusers[0])
        channel_feedback = None
        if event.user:
            channel_feedback = await session.user_channel_create(event.user.id)
        await session.account.protocol.send_message(
            channel_send, f"收到邀请入群事件\n目标群：{event.guild}\n邀请人：{event.user}"
        )

        if channel_feedback:
            await session.account.protocol.send_message(channel_feedback, "请等待机器人管理员处理入群请求")
        await session.account.protocol.send_message(channel_send, "处理请求等待中")

        async def waiter(sess: Session[MessageCreatedEvent]):
            if sess.event.channel.id == channel_send.id:
                return sess.content

        step = step_out(MessageCreatedEvent, waiter, block=True)
        resp = await step.wait(timeout=120)
        if not resp:
            await session.request_approve(False, "管理员超时未回复，请尝试重新发送请求")
            await session.account.protocol.send_message(channel_send, "处理请求超时")
            if channel_feedback:
                await session.account.protocol.send_message(channel_feedback, "管理员超时未回复，请尝试重新发送请求")
            return
        if resp in ("同意", "yes", "y", "ok", "好", "是", "同意请求"):
            await session.request_approve(True)
            await session.account.protocol.send_message(channel_send, "已同意入群请求")
            if channel_feedback:
                await session.account.protocol.send_message(channel_feedback, "管理员已同意入群请求")
            return
        await session.request_approve(False, "管理员拒绝了请求")
        await session.account.protocol.send_message(channel_send, "已拒绝入群请求")
        if channel_feedback:
            await session.account.protocol.send_message(channel_feedback, "管理员已拒绝入群请求")
