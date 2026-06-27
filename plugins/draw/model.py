from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from entari_plugin_user.models import User
from entari_plugin_database import Base


@dataclass
class DrawRecord(Base):
    __tablename__ = "raianbot_draw"

    id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"), primary_key=True)
    """用户 ID"""

    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    """抽签的时间"""

    answer: Mapped[str] = mapped_column(String(64), nullable=False)
    """抽签结果"""
