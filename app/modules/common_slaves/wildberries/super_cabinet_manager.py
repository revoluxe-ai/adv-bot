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


async def get_access_for_wb_cabinet(
    wb_cabinet_id_or_shop_id: int | str,
) -> WBCabinetAccess:

    if isinstance(wb_cabinet_id_or_shop_id, str):
        shop_id: str = wb_cabinet_id_or_shop_id
        stmt = select(WBCabinet.id).where(WBCabinet.shop_id == shop_id)
        async with sm() as session:
            result = await session.execute(stmt)
            wb_cabinet_id = result.scalar()
            if wb_cabinet_id is None:
                raise exceptions.WBCabinetNotFoundError(shop_id)
    else:
        wb_cabinet_id = wb_cabinet_id_or_shop_id

    shop_id_for_deactivate: str | None = None
    async with sm() as session:
        wb_cabinet: WBCabinet | None = await session.get(WBCabinet, wb_cabinet_id)

        if wb_cabinet is None:
            raise exceptions.WBCabinetNotFoundError(wb_cabinet_id)

        shop_id = str(wb_cabinet.shop_id)
        stmt_for_wb_tokens = select(WBToken).where(WBToken.shop_id == shop_id)
        result_for_wb_tokens = await session.execute(stmt_for_wb_tokens)
        wb_tokens: typing.Sequence[WBToken] = result_for_wb_tokens.scalars().all()

        valited_tokens = []
        for token in wb_tokens:
            token.api_key = token.api_key.replace("\r", "").replace("\n", "").strip()
            if not token.check_valid():
                logger.debug(f"Не валидный токен {token.api_key}")
                continue
            if not token.is_personal:
                logger.debug("Не персональный токен, пропускаем: token_id=%s", token.id)
                continue
            if token.shop_id == shop_id:
                valited_tokens.append(token)
        if not valited_tokens:
            return None
        else:
            access = WBCabinetAccess(
                tokens=valited_tokens, wb_user_cabinet=None, wb_cabinet=wb_cabinet
            )
            return access

    


async def get_common_access(client_session: ClientSession) -> WBCabinetAccess:
    stmt = select(WBToken)
    async with sm() as session:
        async for wb_token in await session.stream_scalars(stmt):
            wb_token.api_key = wb_token.api_key.replace("\r", "").replace("\n", "").strip()
            if not wb_token.check_valid():
                logger.debug(f"Не валидный токен {wb_token.api_key}")
                continue
            if not wb_token.is_personal:
                logger.debug(
                    "Не персональный токен в get_common_access, пропускаем: token_id=%s",
                    wb_token.id,
                )
                continue
            result = await token_check_righter.check_all_rights(
                wb_token, client_session
            )
            if result:
                access = WBCabinetAccess(
                    tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None
                )
                return access
    raise ApiForbiddenError("Нет валидных токенов для доступа к API")
