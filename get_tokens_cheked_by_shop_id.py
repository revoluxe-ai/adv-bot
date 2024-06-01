import asyncio

from sqlalchemy import select
from auto_adv_master.modules.common_slaves.wildberries.api_rights import check_token
from auto_adv_master.modules.common_slaves.wildberries.models import WBToken
from auto_adv_master.utils.db.models import User
from auto_adv_master.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker()

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""

shop_id = '8a2acf65-1b2c-4061-9ae5-fed8ffb04371'


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

