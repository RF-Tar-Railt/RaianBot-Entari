from dataclasses import dataclass

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from entari_plugin_database import BaseOrm


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
