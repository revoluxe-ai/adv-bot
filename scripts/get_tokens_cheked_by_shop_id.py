import asyncio
import re
from sqlalchemy import select
from app.modules.common_slaves.wildberries.api_rights import check_token
from app.modules.common_slaves.wildberries.models import WBToken
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker


sm = get_async_session_maker

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""

shop_id = '8f73b031-dc9d-4c77-882a-2780bea125fa'

UUID_REGEX = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

async def get_tokens():
    async with sm() as session:
        stmt = select(WBToken)
        result = await session.execute(stmt)
        tokens = result.scalars().all()

    for token in tokens:
        if token.shop_id != shop_id:
            continue
        try:
            print('Токен найден')
            await check_token(token)
            print(token.api_key)
        except Exception as exc:
            print('Token is not valid')
            print(exc)
    return


if __name__ == '__main__':

    asyncio.run(get_tokens())

