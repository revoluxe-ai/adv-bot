import asyncio
import dataclasses
from typing import Union
from dataclasses import dataclass
from . import exceptions
from .api_rights import TokenRightChecker
from .models import WBToken
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from sqlalchemy import select
from app.utils.db.models import User
import logging



sm = get_async_session_maker()

logger = logging.getLogger(__name__)

@dataclass
class WBCabinetAccess:
    def __repr__(self):
        return  f'ShopId: {self.wb_cabinet.shop_id}'

    tokens: list[WBToken]
    wb_user_cabinet: Union[WBUserCabinet | None]
    wb_cabinet: Union[WBCabinet | None]



async def get_accesses_for_wb_cabinets()-> list[WBCabinetAccess]:
    accesses = []
    async with sm() as session:
        query = select(WBCabinet).options(selectinload(WBCabinet.wb_user_cabinets) \
                                          .selectinload(WBUserCabinet.user) \
                                          .selectinload(User.wb_tokens))

        wb_cabinets = await session.execute(query)
        wb_cabinets = wb_cabinets.scalars().all()
        for wb_cabinet in wb_cabinets:
            wb_user_cabinets = wb_cabinet.wb_user_cabinets
            shop_id = wb_cabinet.shop_id
            tokens_for_wb_cabinet: list[WBToken] = []
            for wb_user_cabinet in wb_user_cabinets:
                user = wb_user_cabinet.user
                tokens: list[WBToken] = user.wb_tokens
                for token in tokens:
                    try:
                        token_shop_id = token.shop_id
                        if shop_id == token_shop_id:
                            tokens_for_wb_cabinet.append(token)
                    except exceptions.TokenExpiredError:
                        logger.error('Срок действия токена истек')
                        checker = TokenRightChecker(token)
                        if await checker.adverts() and await checker.content():
                            tokens_for_wb_cabinet.append(token)

            if tokens_for_wb_cabinet:
                access = WBCabinetAccess(tokens = tokens_for_wb_cabinet,
                                     wb_user_cabinet = None,
                                     wb_cabinet = wb_cabinet)
                accesses.append(access)
    return accesses



async def get_access_for_wb_user_cabinet(wb_user_cabinet: WBUserCabinet):
    async with sm() as session:
        stmt = (
            select(WBUserCabinet)\
            .options(
                selectinload(WBUserCabinet.wb_cabinet),
                selectinload(WBUserCabinet.user)
                .selectinload(User.wb_tokens)  # Загружаем информацию о пользователе
            )
            .where(WBUserCabinet.id == wb_user_cabinet.id)  # Условие должно быть скорректировано
        )
        result = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result.scalars().first()
        user = wb_user_cabinet.user
        tokens = user.wb_tokens
        wb_cabinet = wb_user_cabinet.wb_cabinet
        access = WBCabinetAccess(tokens = tokens,
                                 wb_user_cabinet = wb_user_cabinet,
                                 wb_cabinet = wb_cabinet)

        return access


async def get_super_user_access():
    accesses = await get_accesses_for_wb_cabinets()
    tokens = [token for access in accesses for token in access.tokens]
    leave_tokens = []
    for token in tokens:
        while True:
            try:
                checker = TokenRightChecker(token)
                if await checker.adverts() and await checker.content():
                    leave_tokens.append(token)
                    break
            except Exception as exc:
                logger.error(exc)
                await asyncio.sleep(1)


    super_user_access = WBCabinetAccess(tokens = leave_tokens,
                                        wb_user_cabinet = None,
                                        wb_cabinet = None)

    return super_user_access