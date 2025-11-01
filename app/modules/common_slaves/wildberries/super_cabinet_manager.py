import datetime
import logging
import typing
from dataclasses import dataclass
from unittest.mock import Mock

from aiohttp import ClientSession
from sqlalchemy import select

from app.configs.infrastructure_config.wb_config import WBConfig
from dependency_injector.wiring import Provide
from app.core.di.app_container import AppContainer
from app.core.wb_api.check_righter import CheckRighter
from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from . import exceptions
from .models import WBToken

sm = get_async_session_maker

logger = logging.getLogger(__name__)


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
    wb_config: WBConfig = Provide[AppContainer.settings.provided.infrastructure.wb],
) -> WBCabinetAccess:

    if wb_config.test_mode:
        test_shop_id = "b90b2506-25e9-444a-aa2c-38e2e628f139"
        wb_token_mock = Mock(spec=WBToken)
        wb_token_mock.api_key = wb_config.test_token
        wb_token_mock.hash = hash(wb_config.test_token)
        wb_token_mock.expires = datetime.datetime.now() + datetime.timedelta(days=30)
        wb_token_mock.shop_id = test_shop_id
        wb_token_mock.is_expired = False
        wb_cabinet_mock = Mock()
        wb_cabinet_mock.shop_id = test_shop_id
        access = WBCabinetAccess([wb_token_mock], None, wb_cabinet_mock)
        return access

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
        wb_cabinet: WBCabinet | None = await session.get(WBCabinet, wb_cabinet_id)

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


async def get_common_access(client_session: ClientSession) -> WBCabinetAccess:
    stmt = select(WBToken)
    async with sm() as session:
        async for wb_token in await session.stream_scalars(stmt):
            if not wb_token.check_valid():
                logger.debug(f"Не валидный токен {wb_token.api_key}")
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
