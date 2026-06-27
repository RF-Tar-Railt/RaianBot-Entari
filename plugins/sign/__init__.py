import random
from datetime import datetime

from arclet.alconna import CommandMeta
from arclet.entari import plugin, command, metadata, plugin_config

from entari_plugin_database import AsyncSession
from entari_plugin_user import UserSession
from entari_plugin_llm.event import LLMCollectVariableEvent

from .config import SignConfig
from .model import SignRecord

metadata(
    name="签到",
    description="每天一次的签到，签到后可以获得信赖值，信赖值可以改变对话的语气",
    author=[{"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"}],
    config=SignConfig,
)

cfg = plugin_config(SignConfig)


@command.on("签到", meta=CommandMeta("在机器人处登记用户信息"))
async def sign_up(db_sess: AsyncSession, user_sess: UserSession):
    """在机器人处登记信息"""
    async with db_sess.begin():
        record = await db_sess.get(SignRecord, user_sess.user_id)
        if record:
            today = datetime.now()
            if record.date.day == today.day and record.date.month == today.month:
                return "您今天已与我签到!"
            record.date = today
            record.count += 1
            if record.trust < cfg.max:
                record.trust += round(random.randint(1, 10) / 6.25, 3)
                return f"签到成功！\n当前信赖值：<b>{record.trust:.3f}</b>"
            else:
                return "签到成功！\n您的信赖已满！"
        else:
            record = SignRecord(id=user_sess.user_id)
            db_sess.add(record)
            return "初次签到成功！\n当前信赖值：<b>1</b>"


@plugin.listen(LLMCollectVariableEvent)
async def collect_trust(db_sess: AsyncSession, user_sess: UserSession):
    async with db_sess.begin():
        record = await db_sess.get(SignRecord, user_sess.user_id)
        if record:
            return {"trust": round(record.trust / cfg.max, 2)}
        else:
            return {"trust": round(1.0 / cfg.max, 2)}
