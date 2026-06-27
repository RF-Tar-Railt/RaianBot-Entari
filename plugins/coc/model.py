from dataclasses import dataclass

from sqlalchemy import Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from entari_plugin_database import Base


@dataclass
class CocRule(Base):
    __tablename__ = "raianbot_coc"

    platform: Mapped[str] = mapped_column(String, primary_key=True)
    """平台"""

    channel_id: Mapped[str] = mapped_column(String, primary_key=True)
    """频道 ID"""

    rule: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    """房规"""
