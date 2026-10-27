from dataclasses import dataclass

from alembic.operations import Operations
from entari_plugin_database import BaseOrm, register_custom_migration
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import update


@dataclass
class WeiboSubscribe(BaseOrm):
    __tablename__ = "entari_plugin_sim_weibo.subscribe"

    login_id: Mapped[str] = mapped_column(String, primary_key=True)
    """登录 ID"""

    platform: Mapped[str] = mapped_column(String, primary_key=True)
    """平台"""

    channel_id: Mapped[str] = mapped_column(String, primary_key=True)
    """频道 ID"""

    wid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """微博用户 ID"""


@register_custom_migration(WeiboSubscribe, "upgrade", script_rev="replace_platform_1", replace=False)
def replace_platform_1(ops: Operations, ctx, table):
    ops.execute(update(WeiboSubscribe).where(WeiboSubscribe.platform == "milky").values(platform="qq-client"))
