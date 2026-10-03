"""Доступ к WB-кабинету: выбор валидных personal-токенов и deactivate при их отсутствии."""

import logging
import typing
from dataclasses import dataclass

from aiohttp import ClientSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.wb_api.check_righter import CheckRighter
from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.token_monitoring.models import NotificationType
from app.modules.token_monitoring.services.cabinet_status_service import (
    deactivate_cabinet_atomic_with_user_trackers,
)
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker
from . import exceptions
from .models import WBToken
from .models.wb_cabinet import WBCabinet

sm = get_async_session_maker

logger = logging.getLogger(__name__)


async def get_shop_ids_with_active_tokens(
    session: AsyncSession, shop_ids: list[str]
) -> set[str]:
    """Return set of shop_id that have at least one WBToken with active=True."""
    if not shop_ids:
        return set()
    stmt = (
        select(WBToken.shop_id)
        .where(WBToken.shop_id.in_(shop_ids), WBToken.active.is_(True))
        .distinct()
    )
    result = await session.execute(stmt)
    return {s for s in result.scalars().all() if s is not None}


token_check_righter = CheckRighter()


@dataclass
class WBCabinetAccess:
    tokens: list[WBToken]
    wb_user_cabinet: WBUserCabinet | None
    wb_cabinet: WBCabinet | None

    @property
    def shop_id(self) -> str:
        if self.wb_cabinet:
            return str(self.wb_cabinet.shop_id)
        else:
            return "Не определен"


async def resolve_wb_cabinet_id_by_shop_id_in_session(
    session: AsyncSession, shop_id: str
) -> int:
    """Resolve WBCabinet.id for shop_id (PURE_READ).

    Args:
        session: injectable async session (caller: ``sm(read_only=True)``).
        shop_id: WB shop identifier string.

    Returns:
        WBCabinet primary key.

    Raises:
        WBCabinetNotFoundError: when shop_id has no cabinet row.
    """
    stmt = select(WBCabinet.id).where(WBCabinet.shop_id == shop_id)
    result = await session.execute(stmt)
    wb_cabinet_id = result.scalar()
    if wb_cabinet_id is None:
        raise exceptions.WBCabinetNotFoundError(shop_id)
    return int(wb_cabinet_id)


def _token_keeps_cabinet_running(token: WBToken, shop_id: str) -> bool:
    """Токен пригоден для работы бота: personal либо «только чтение».

    ``read_only`` — бит JWT «Токен только на чтение», не режим сессии Postgres.
    Такой токен не считается поводом выключать магазин.
    """
    if token.shop_id != shop_id:
        return False
    if token.is_personal:
        return True
    try:
        return bool(token.read_only)
    except Exception:
        logger.debug(
            "Не удалось прочитать read_only, пропускаем: token_id=%s", token.id
        )
        return False


async def load_wb_cabinet_access_in_session(
    session: AsyncSession, wb_cabinet_id: int
) -> WBCabinetAccess | str:
    """Прочитать доступ кабинета. Сессия только на чтение, без деактивации.

    Args:
        session: injectable async session (``sm(read_only=True)``).
        wb_cabinet_id: первичный ключ WBCabinet.

    Returns:
        WBCabinetAccess, если есть personal-токен или токен «только чтение»;
        иначе строка shop_id. Кабинет эта функция не выключает.

    Raises:
        WBCabinetNotFoundError: кабинет не найден.
    """
    wb_cabinet: WBCabinet | None = await session.get(WBCabinet, wb_cabinet_id)

    if wb_cabinet is None:
        raise exceptions.WBCabinetNotFoundError(wb_cabinet_id)

    shop_id = str(wb_cabinet.shop_id)
    stmt_for_wb_tokens = select(WBToken).where(WBToken.shop_id == shop_id)
    result_for_wb_tokens = await session.execute(stmt_for_wb_tokens)
    wb_tokens: typing.Sequence[WBToken] = result_for_wb_tokens.scalars().all()

    valited_tokens: list[WBToken] = []
    for token in wb_tokens:
        token.api_key = token.api_key.replace("\r", "").replace("\n", "").strip()
        if not token.check_valid():
            logger.debug("Не валидный токен, пропускаем: token_id=%s", token.id)
            continue
        if not _token_keeps_cabinet_running(token, shop_id):
            logger.debug(
                "Токен без personal и без чтения, пропускаем: token_id=%s",
                token.id,
            )
            continue
        valited_tokens.append(token)
    if not valited_tokens:
        return shop_id

    return WBCabinetAccess(
        tokens=valited_tokens, wb_user_cabinet=None, wb_cabinet=wb_cabinet
    )


async def find_common_access_token_in_session(
    session: AsyncSession,
    client_session: ClientSession,
) -> WBToken | None:
    """Вернуть первый валидный personal-токен с правами общего доступа."""
    stmt = select(WBToken)
    async for wb_token in await session.stream_scalars(stmt):
        wb_token.api_key = wb_token.api_key.replace("\r", "").replace("\n", "").strip()
        if not wb_token.check_valid():
            logger.debug(
                "Не валидный токен, пропускаем: token_id=%s", wb_token.id
            )
            continue
        if not wb_token.is_personal:
            logger.debug(
                "Не персональный токен в get_common_access, пропускаем: token_id=%s",
                wb_token.id,
            )
            continue
        result = await token_check_righter.check_all_rights(wb_token, client_session)
        if result:
            return wb_token
    return None


async def get_access_for_wb_cabinet(
    wb_cabinet_id_or_shop_id: int | str,
) -> WBCabinetAccess | None:
    """Собрать доступ к кабинету. Read-only токен оставляет магазин включённым.

    Чтение идёт через ``sm(read_only=True)``. Запись и деактивация — только
    если нет ни personal-токена, ни токена «только чтение».

    Args:
        wb_cabinet_id_or_shop_id: id кабинета или shop_id.

    Returns:
        Доступ с пригодными токенами.

    Raises:
        WBCabinetNotFoundError: кабинет не найден.
        ApiForbiddenError: пригодного токена нет; кабинет при этом выключается.
    """
    if isinstance(wb_cabinet_id_or_shop_id, str):
        shop_id: str = wb_cabinet_id_or_shop_id
        async with sm(read_only=True) as session:
            wb_cabinet_id = await resolve_wb_cabinet_id_by_shop_id_in_session(
                session, shop_id
            )
    else:
        wb_cabinet_id = wb_cabinet_id_or_shop_id

    async with sm(read_only=True) as session:
        access_or_shop = await load_wb_cabinet_access_in_session(session, wb_cabinet_id)
        if isinstance(access_or_shop, WBCabinetAccess):
            return access_or_shop
        shop_id_for_deactivate = access_or_shop

    async with sm(read_only=False) as session:
        wb_cabinet = await session.get(WBCabinet, wb_cabinet_id)
        if wb_cabinet is not None:
            wb_cabinet.active = False
            await session.commit()

    await deactivate_cabinet_atomic_with_user_trackers(
        shop_id_for_deactivate,
        notification_type=NotificationType.TOKEN_DEACTIVATED.value,
    )
    raise ApiForbiddenError(
        f"Нет валидных токенов для кабинета с shop_id {shop_id_for_deactivate}"
    )


async def get_common_access(client_session: ClientSession) -> WBCabinetAccess:
    """Открыть read-only PG-сессию и вернуть общий доступ по валидному токену."""
    async with sm(read_only=True) as session:
        wb_token = await find_common_access_token_in_session(session, client_session)
        if wb_token is not None:
            return WBCabinetAccess(
                tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None
            )
    raise ApiForbiddenError("Нет валидных токенов для доступа к API")
