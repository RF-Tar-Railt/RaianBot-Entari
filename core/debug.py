from __future__ import annotations


from arclet.letoderea import BLOCK
from arclet.entari import Entari, MessageCreatedEvent, Session, plugin, command
from arclet.entari.filter import admins
from arclet.entari.event.send import SendResponse
from entari_plugin_database import AsyncSession, select
from entari_plugin_user.models import User, Bind
from sqlalchemy import func


@plugin.listen(MessageCreatedEvent, priority=0)
async def protect(sess: Session):
    if sess.account.platform in ("onebot", "milky") and sess.event.user and sess.event.user.id == "3382510837":
        return BLOCK


@plugin.listen(MessageCreatedEvent, priority=1)
async def record_recv(app: Entari):
    recv = await app.cache.get("recv", 0)
    await app.cache.set("recv", recv + 1)


@plugin.listen(SendResponse, priority=1)
async def record_sent(app: Entari):
    sent = await app.cache.get("sent", 0)
    await app.cache.set("sent", sent + 1)


@command.command("调试", "显示调试信息")
@admins()
async def debug(sess: Session, app: Entari, db_sess: AsyncSession):
    async with db_sess.begin():
        stmt = (
            select(func.count("*"))
            .select_from(User)
            .join(Bind, User.id == Bind.bind_id)
            .where(Bind.platform == sess.account.platform)
        )
        user_count = await db_sess.scalar(stmt)
    guilds = [guild async for guild in sess.account.guild_list()]
    channels = [channel for guild in guilds async for channel in sess.account.channel_list(guild.id)]
    return (
        f"{sess.account.self_info.user.name or sess.account.self_info.platform} ({sess.account.self_id}) 调试信息\n"
        f"当前共加载模块：     {len(plugin.get_plugins())} 个\n"
        f"当前共加入群与频道：  {len(guilds)} | {len(channels)} 个\n"
        f"参与机器人交互的用户：{user_count} 人\n"
        f"自启动后共收到消息：  {await app.cache.get('recv', 0)} 条\n"
        f"自启动后共发出消息：  {await app.cache.get('sent', 0)} 条"
    )
