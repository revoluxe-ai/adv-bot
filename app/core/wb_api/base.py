import logging
from abc import ABC
from typing import Generator

from app.utils.db.session_maker import get_async_session_maker as sm
from .exceptions import ApiForbiddenError
from ...modules.common_slaves.wildberries.ABC_WB_API import Headers
from ...modules.common_slaves.wildberries.models import WBCabinet, WBToken
from ...modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess

logger = logging.getLogger(__name__)


class BaseAPI(ABC):

    def __init__(self, wb_access: WBCabinetAccess):
        tokens: list[WBToken] = wb_access.tokens
        self.access = wb_access
        if not tokens:
            raise ApiForbiddenError(
                "Нет токенов для доступа к API",
                wb_user_cabinet=wb_access.wb_user_cabinet,
            )
        tokens = sorted(tokens, key=lambda x: x.expires, reverse=True)
        self._free_tokens = tokens
        current_token = self._free_tokens.pop()
        self.headers = Headers(current_token)
        self.shop_id = current_token.shop_id

    @staticmethod
    def chunks(lst, n) -> Generator [list, None]:
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    async def set_next_token(self) -> None:
        if self._free_tokens:
            self.headers = Headers(self._free_tokens.pop())
        else:
            wb_cabinet: WBCabinet = self.access.wb_cabinet
            try:
                async with sm(read_only=False) as session:
                    fresh_cabinet = await session.get(WBCabinet, wb_cabinet.id)
                    if fresh_cabinet:
                        fresh_cabinet.active = False
                        await session.commit()
            except Exception as e:
                logger.error(
                    f"Ошибка при отключении кабинета {wb_cabinet.shop_id}: {e}",
                    exc_info=True,
                )
                raise e
            raise ApiForbiddenError(
                "Нет свободных токенов", wb_user_cabinet=self.access.wb_cabinet
            )
