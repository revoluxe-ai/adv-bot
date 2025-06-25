import asyncio

from sqlalchemy import select

from app.modules.common_slaves.wildberries.api_rights import check_token
from app.modules.common_slaves.wildberries.models import WBToken
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""


shop_id = "89b37551-ff7f-4124-ac7e-cd7546af25cf"


async def get_tokens():
    async with sm() as session:
        stmt = select(WBToken)
        result = await session.execute(stmt)
        tokens = result.scalars().all()

    for token in tokens:
        if token.shop_id != shop_id:
            continue
        try:
            print("Токен найден")
            await check_token(token)
            print(token.api_key)
        except Exception as exc:
            print("Token is not valid")
            print(exc)
            del exc
    return


if __name__ == "__main__":
    asyncio.run(get_tokens())
