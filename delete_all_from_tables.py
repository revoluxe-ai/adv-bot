import asyncio

from sqlalchemy import text

from app.utils.db.session_maker import get_async_session_maker



sm = get_async_session_maker()

async def delete_all_from_tables():
    async with sm() as session:
        await session.execute(text('DELETE FROM advkeyword'))
        await session.execute(text('DELETE FROM keywordsetting'))
        await session.execute(text('DELETE FROM wbcard'))
        await session.execute(text('DELETE FROM advsetting'))
        await session.execute(text('DELETE FROM wbcategory'))
        await session.execute(text('DELETE FROM wbtoken'))
        await session.execute(text('DELETE FROM wbusercabinet'))
        await session.execute(text('DELETE FROM wbcabinet'))

        await session.commit()







if __name__ == '__main__':
    asyncio.run(delete_all_from_tables())