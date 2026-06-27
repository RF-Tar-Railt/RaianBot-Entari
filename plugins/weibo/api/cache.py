from sqlalchemy.sql import select
from entari_plugin_database import service as db_service

from .model import WeiboUser


class WeiboUserCache:
    def __init__(self):
        self.data = {}

    async def load(self):
        users = await db_service.select_all(select(WeiboUser))
        self.data = {str(user.id): user for user in users}

    def get(self, wid: int):
        return self.data.get(str(wid))

    async def merge(self, user: WeiboUser):
        async with db_service.get_session() as session:
            if str(user.id) not in self.data:
                self.data[str(user.id)] = user
                session.add(user)
                await session.commit()
            else:
                await session.merge(user)
                await session.commit()

    async def save(self):
        async with db_service.get_session() as session:
            for user in self.data.values():
                await session.merge(user)
                await session.commit()
