from entari_plugin_database import get_session, select
from entari_plugin_user.models import Bind


async def get_bind_by_user_id(user_id: int) -> Bind | None:
    async with get_session() as db_session:
        return (await db_session.scalars(select(Bind).where(Bind.bind_id == user_id))).one_or_none()
