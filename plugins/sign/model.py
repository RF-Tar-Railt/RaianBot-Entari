from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Float, text, func
from sqlalchemy.orm import Mapped, mapped_column
from entari_plugin_database import Base
from entari_plugin_user.models import User


@dataclass
class SignRecord(Base):
    __tablename__ = "raianbot_sign"

    id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"), primary_key=True)
    """用户 ID"""

    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    """签到日期"""

    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    """签到次数"""

    trust: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1.0"))
    """用户信任度"""
