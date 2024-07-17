import asyncio
import datetime
import logging
import typing
from dataclasses import dataclass
from typing import Union, AsyncGenerator

import aiohttp
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.client_bot.const import MAX_TOKENS
from app.client_bot.wb_user_cabinet_manager import CabinetManager
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from . import api_rights, exceptions
from .api_rights import check_token
from .exceptions import ApiForbiddenError, UnknownApiRequestError
from .models import WBToken

sm = get_async_session_maker

logger = logging.getLogger(__name__)

@dataclass
class WBCabinetAccess:
    def __repr__(self):
        return  f'ShopId: {self.wb_cabinet.shop_id}'

    tokens: list[WBToken]
    wb_user_cabinet: Union[WBUserCabinet | None]
    wb_cabinet: Union[WBCabinet | None]



async def get_accesses_for_wb_cabinets(semaphore: asyncio.Semaphore)-> AsyncGenerator[WBCabinetAccess, None]:
    async with sm(semaphore) as session:
        query = select(WBCabinet).options(selectinload(WBCabinet.wb_user_cabinets) \
                                          .selectinload(WBUserCabinet.user) \
                                          .selectinload(User.wb_tokens))\
        .where(or_(WBCabinet.expiration_time >= datetime.datetime.now(),
                   WBCabinet.balance > 0))

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
                        logger.error('Срок действия токена истек')
                        continue
                    if token_shop_id != shop_id:
                        continue
                    try:
                        await api_rights.check_token(token)
                        users_live_tokens.append(token)
                    except ApiForbiddenError as exc:
                        logger.debug(exc)
                        token.active = False
                        await session.commit()
                        continue

                    except UnknownApiRequestError as e:
                        logger.error(e)
                        users_live_tokens.append(token)
                    except aiohttp.client_exceptions.ServerDisconnectedError as e:
                        logger.error(e)
                        users_live_tokens.append(token)
                    except aiohttp.client_exceptions.ClientOSError as e:
                        logger.error(e)
                        users_live_tokens.append(token)
                    finally:
                        await asyncio.sleep(1)
                tokens_for_wb_cabinet.extend(users_live_tokens)

            if tokens_for_wb_cabinet:
                access = WBCabinetAccess(tokens = tokens_for_wb_cabinet,
                                     wb_user_cabinet = None,
                                     wb_cabinet = wb_cabinet)
                yield access





async def get_access_for_wb_user_cabinet(wb_user_cabinet: WBUserCabinet)-> WBCabinetAccess:
    async with sm() as session:
        stmt = select(WBCabinet).join(WBUserCabinet)\
           .where(WBCabinet.id == wb_user_cabinet.wb_cabinet_id)
        result = await session.execute(stmt)
        wb_cabinet: WBCabinet = result.scalars().first()
        stmt = select(WBToken)
        result = await session.execute(stmt)
        tokens: list[WBToken] = result.scalars().all()
    checked_tokens = []
    for token in tokens:
        if token.shop_id == wb_cabinet.shop_id:
            try:
                await check_token(token)
            except exceptions.ApiForbiddenError:
                logger.debug('ApiForbiddenError')
                token.active = False
                await session.commit()
                continue
            checked_tokens.append(token)
        else:
            continue


    access = WBCabinetAccess(tokens = checked_tokens,
                             wb_user_cabinet = None,
                             wb_cabinet = wb_cabinet)
    return access



async def get_super_user_access():

    leave_tokens = []
    access_generator = get_accesses_for_wb_cabinets()

    async for access in access_generator:
        for token in access.tokens:
            try:
                await CabinetManager.check_access(token)
                leave_tokens.append(token)
                if len(leave_tokens) >= MAX_TOKENS:
                    break
            except Exception as exc:
                logger.debug(f'Токен не прошел проверку: {exc}')
                await asyncio.sleep(0)

        if len(leave_tokens) >= MAX_TOKENS:
            await access_generator.aclose()
            break

    return WBCabinetAccess(tokens=leave_tokens, wb_user_cabinet=None, wb_cabinet=None)


async def get_access_for_wb_cabinet(wb_cabinet_id: int) -> Union[WBCabinetAccess, None]:
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

        return WBCabinetAccess(
            tokens=live_tokens, wb_user_cabinet=None, wb_cabinet=wb_cabinet
        ) if live_tokens else None
