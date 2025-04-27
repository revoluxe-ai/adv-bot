import logging
import typing
from dataclasses import dataclass

from sqlalchemy import select

from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from . import exceptions
from .models import WBToken

sm = get_async_session_maker

logger = logging.getLogger(__name__)


@dataclass
class WBCabinetAccess:
    tokens: list[WBToken]
    wb_user_cabinet: typing.Union[WBUserCabinet]
    wb_cabinet: typing.Union[WBCabinet]


async def get_access_for_wb_cabinet(
    wb_cabinet_id_or_shop_id: typing.Union[int, str],
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

    async with sm() as session:
        stmt_wb_cabinet_getting = select(WBCabinet).where(WBCabinet.id == wb_cabinet_id)
        result_from_pg = await session.execute(stmt_wb_cabinet_getting)
        wb_cabinet: WBCabinet | None = result_from_pg.scalar()

        if wb_cabinet is None:
            raise exceptions.WBCabinetNotFoundError(wb_cabinet_id)

        shop_id = str(wb_cabinet.shop_id)
        stmt_for_wb_tokens = select(WBToken).where(WBToken.shop_id == shop_id)
        result_for_wb_tokens = await session.execute(stmt_for_wb_tokens)
        wb_tokens: typing.Sequence[WBToken] = result_for_wb_tokens.scalars().all()

        valited_tokens = []
        for token in wb_tokens:
            if not token.check_valid():
                logger.debug(f"Не валидный токен {token.api_key}")
                continue
            if token.shop_id == shop_id:
                valited_tokens.append(token)
        if not valited_tokens:
            raise ApiForbiddenError(
                f"Нет валидных токенов для кабинета с shop_id {shop_id}"
            )
        access = WBCabinetAccess(
            tokens=valited_tokens, wb_user_cabinet=None, wb_cabinet=wb_cabinet
        )
        return access
