from sqlalchemy import select

from app.my_types import WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker()



"""
Только для простых данных!

"""

async def get_user_cabinet_names(user_id: int) -> list[str]:
    async with sm() as session:
        stmt = select(WBUserCabinet)\
            .where(WBUserCabinet.user_id == user_id)
        result = await session.execute(stmt)
        cabinet_ids = result.scalars().all()
        cabinet_names = []
        for cabinet_id in cabinet_ids:
            stmt = select(new.types.WBCabinet).where(new.types.WBCabinet.id == cabinet_id)
            result = await session.execute(stmt)
            cabinet_name = result.scalar()
            cabinet_names.append(cabinet_name)
        return cabinet_names