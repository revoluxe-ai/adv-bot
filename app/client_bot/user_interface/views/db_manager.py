from app.utils.db.session_maker import get_async_session_maker


_sm = get_async_session_maker()


async def get_ref_statistic(user_telegram_id):
    async with _sm() as session:
        ...
