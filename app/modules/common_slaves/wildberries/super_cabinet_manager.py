import asyncio
import datetime
import logging
import typing
from dataclasses import dataclass

import aiohttp
from aiohttp import ServerTimeoutError
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload, joinedload

from app.client_bot.const import MAX_TOKENS
from app.client_bot.wb_user_cabinet_manager import CabinetManager
from . import exceptions
from .exceptions import ApiForbiddenError, UnknownApiRequestError, NotValidTokenError
from .models import WBToken, AdvSetting
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from sqlalchemy import select
from app.utils.db.models import User
import logging
import aiohttp


sm = get_async_session_maker

logger = logging.getLogger(__name__)

@dataclass
class WBCabinetAccess:
    def __repr__(self):
        return  f'ShopId: {self.wb_cabinet.shop_id}'

    tokens: list[WBToken]
    wb_user_cabinet: typing.Union[WBUserCabinet | None]
    wb_cabinet: typing.Union[WBCabinet | None]



async def get_accesses_for_bidder(semaphore: asyncio.Semaphore = None)-> typing.AsyncGenerator[WBCabinetAccess, None]:
    async with sm(semaphore) as session:
        query = select(WBCabinet).options(selectinload(WBCabinet.wb_user_cabinets) \
                                          .selectinload(WBUserCabinet.user) \
                                          .selectinload(User.wb_tokens),
                                          selectinload(WBCabinet.adv_settings))\
        .where(or_(WBCabinet.expiration_time >= datetime.datetime.now(),
                   WBCabinet.balance > 0,
                   WBCabinet.bonus > 0))

        wb_cabinets = await session.execute(query)
        wb_cabinets = wb_cabinets.scalars().all()


        for wb_cabinet in wb_cabinets:
            stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id,
                                            AdvSetting.bidder_active == True)
            result = await session.execute(stmt)
            adv_settings = result.scalars().all()
            if not adv_settings:
                continue
            wb_user_cabinets = wb_cabinet.wb_user_cabinets
            shop_id = wb_cabinet.shop_id
            tokens_for_wb_cabinet: list[WBToken] = []
            for wb_user_cabinet in wb_user_cabinets:
                user = wb_user_cabinet.user
                tokens: list[WBToken] = user.wb_tokens
                users_live_tokens = []
                for token in tokens:
                    if not token.active:
                        continue
                    try:
                        token_shop_id = token.shop_id# Используйте total_clicks для суммы кликов
                    except exceptions.TokenExpiredError:
                        logger.error('Срок действия токена истек')
                        continue
                    if token_shop_id != shop_id:
                        continue
                    users_live_tokens.append(token)
                tokens_for_wb_cabinet.extend(users_live_tokens)

            if tokens_for_wb_cabinet:
                access = WBCabinetAccess(tokens = tokens_for_wb_cabinet,
                                     wb_user_cabinet = None,
                                     wb_cabinet = wb_cabinet)
                yield access
    return


async def get_accesses_for_wb_cabinets()-> typing.AsyncGenerator[WBCabinetAccess, None]:
    async with sm() as session:
        query = select(WBCabinet).options(selectinload(WBCabinet.wb_user_cabinets) \
                                          .selectinload(WBUserCabinet.user) \
                                          .selectinload(User.wb_tokens))\
        .where(or_(WBCabinet.expiration_time >= datetime.datetime.now(),
                   WBCabinet.balance > 0,
                   WBCabinet.bonus > 0))

        wb_cabinets = await session.execute(query)
        wb_cabinets = wb_cabinets.scalars().all()
    for wb_cabinet in wb_cabinets:
        wb_user_cabinets = wb_cabinet.wb_user_cabinets
        shop_id = wb_cabinet.shop_id
        tokens_for_wb_cabinet: list[WBToken] = []
        for wb_user_cabinet in wb_user_cabinets:
            user = wb_user_cabinet.user
            tokens: list[WBToken] = user.wb_tokens
            users_live_tokens = []
            for token in tokens:
                if not token.active:
                    continue
                try:
                    token_shop_id = token.shop_id# Используйте total_clicks для суммы кликов
                except exceptions.TokenExpiredError:
                    logger.debug('Срок действия токена истек')
                    token.active = False
                    await session.commit()
                    continue
                except NotValidTokenError:
                    logger.debug('Токен не прошел проверку')
                    token.active = False
                    await session.commit()
                    continue
                if token_shop_id != shop_id:
                    continue
                users_live_tokens.append(token)
            tokens_for_wb_cabinet.extend(users_live_tokens)

        if tokens_for_wb_cabinet:
            access = WBCabinetAccess(tokens = tokens_for_wb_cabinet,
                                 wb_user_cabinet = None,
                                 wb_cabinet = wb_cabinet)
            yield access
    return


async def get_access_for_wb_user_cabinet(wb_user_cabinet: WBUserCabinet)-> WBCabinetAccess:
    async with sm() as session:
        stmt = (
            select(WBUserCabinet)\
            .options(
                joinedload(WBUserCabinet.wb_cabinet),
                selectinload(WBUserCabinet.user)
                .selectinload(User.wb_tokens)  # Загружаем информацию о пользователе
            )
            .where(WBUserCabinet.id == wb_user_cabinet.id)  # Условие должно быть скорректировано
        )
        result = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result.scalars().first()
        stmt = select(WBToken)
        result = await session.execute(stmt)
        tokens: list[WBToken] = result.scalars().all()
    wb_cabinet = wb_user_cabinet.wb_cabinet
    checked_tokens = []
    for token in tokens:
        if token.shop_id == wb_cabinet.shop_id:
            checked_tokens.append(token)
        else:
            continue


    access = WBCabinetAccess(tokens = checked_tokens,
                             wb_user_cabinet = None,
                             wb_cabinet = wb_cabinet)
    return access


async def get_super_user_access():
    leave_tokens = []
    accesses_gen = get_accesses_for_wb_cabinets()
    async for access in accesses_gen:
        tokens = access.tokens
        for token in tokens:
                try:
                    await CabinetManager.check_access(token)
                    leave_tokens.append(token)
                    if len(leave_tokens) >= MAX_TOKENS:
                        break
                except Exception as exc:
                    logger.debug(f'Токен не прошел проверку: {exc}')
                    await asyncio.sleep(0)

    super_user_access = WBCabinetAccess(tokens = leave_tokens,
                                        wb_user_cabinet = None,
                                        wb_cabinet = None)

    return super_user_access


async def get_access_for_wb_cabinet(wb_cabinet_id: int)->WBCabinetAccess:
    async with sm() as session:
        stmt = (
            select(WBCabinet)
            .options(selectinload(WBCabinet.wb_user_cabinets)
                     .selectinload(WBUserCabinet.user)
                     .selectinload(User.wb_tokens))
            .where(WBCabinet.id == wb_cabinet_id)
        )
        result = await session.execute(stmt)
        wb_cabinet: WBCabinet = result.scalars().first()
        wb_user_cabinets = wb_cabinet.wb_user_cabinets
        tokens = []
        for wb_user_cabinet in wb_user_cabinets:
            user = wb_user_cabinet.user
            user_tokens = user.wb_tokens
            tokens.extend(user_tokens)
        live_tokens = []
        for token in user_tokens:
            try:
                await CabinetManager.check_access(token)
                live_tokens.append(token)
            except Exception as exc:
                logger.error(f'Токен не прошел проверку: {exc}')
                continue
        if live_tokens:
            access = WBCabinetAccess(tokens = live_tokens,
                                     wb_user_cabinet = None,
                                     wb_cabinet = wb_cabinet)
            return access