from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from entari_plugin_database import Base
from entari_plugin_user.models import User


@dataclass
class SKAutoSignRecord(Base):
    __tablename__ = "raianbot_sk_autosign"

    id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"), primary_key=True)
    """用户 ID"""

    token: Mapped[str] = mapped_column(String(256), nullable=False)
    """森空岛token"""


@dataclass
class SKAutoSignResultRecord(Base):
    __tablename__ = "raianbot_sk_autosign_result"

    id: Mapped[int] = mapped_column(ForeignKey(SKAutoSignRecord.id, ondelete="CASCADE"), primary_key=True)
    """用户 ID"""

    uid: Mapped[str] = mapped_column(String(256), primary_key=True)
    """玩家 ID"""

    date: Mapped[datetime] = mapped_column(DateTime, nullable=True, server_default=func.now())
    """签到时间"""

    result: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    """结果"""
