from typing import Literal
from dataclasses import dataclass, field, asdict
from satori.model import ModelBase
from sqlalchemy.types import Integer, BigInteger, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from entari_plugin_database import BaseOrm

MAPPING = {
    "info": 100505,
    "profile": 230283,
    "weibo": 107603,
    "video": 231567,
    "album": 107803,
}


@dataclass
class WeiboUser(BaseOrm):
    __tablename__ = "entari_plugin_sim_weibo.user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    avatar: Mapped[str] = mapped_column(String, default="")
    statuses: Mapped[int] = mapped_column(Integer, default=0)
    visitable: Mapped[bool] = mapped_column(Boolean, default=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    latest: Mapped[str] = mapped_column(String, default="")

    @property
    def info_link(self):
        return f"https://m.weibo.cn/u/{self.id}"

    @property
    def info_data(self):
        return f"https://m.weibo.cn/api/container/getIndex?{self.contain_id('info')}"

    def contain_id(self, keys: Literal["info", "profile", "weibo", "video", "album"]) -> str:
        return f"{MAPPING[keys]}{self.id}"

    def copy(self):
        return WeiboUser(
            id=self.id,
            name=self.name,
            description=self.description,
            avatar=self.avatar,
            statuses=self.statuses,
            visitable=self.visitable,
            total=self.total,
            latest=self.latest,
        )


@dataclass
class WeiboPost(ModelBase):
    bid: str
    text: str
    img_urls: list[str] = field(default_factory=list)
    video_url: str | None = field(default=None)
    retweet: "WeiboPost | None" = field(default=None)
    user: WeiboUser | None = field(default=None)

    @property
    def url(self) -> str:
        return f"https://m.weibo.cn/status/{self.bid}"

    __converter__ = {"user": lambda *args, **kwargs: WeiboUser(**kwargs)}

    def dump(self) -> dict:
        return {
            "bid": self.bid,
            "text": self.text,
            "img_urls": self.img_urls,
            "video_url": self.video_url,
            "retweet": self.retweet.dump() if self.retweet else None,
            "user": asdict(self.user) if self.user else None,
        }


WeiboPost.__converter__["retweet"] = WeiboPost.parse
