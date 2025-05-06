import logging
from typing import Generator, TypeVar

from app.utils.db.session_maker import get_async_session_maker as sm
from .exceptions import ApiForbiddenError
from ...modules.common_slaves.wildberries.ABC_WB_API import Headers
from ...modules.common_slaves.wildberries.models import WBCabinet, WBToken
from ...modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess

logger = logging.getLogger(__name__)


T = TypeVar("T")


class BaseAPI:
    HOST = "wildberries.ru"

    def __init__(self, wb_access: WBCabinetAccess) -> None:
        tokens: list[WBToken] = wb_access.tokens
        self.access: WBCabinetAccess = wb_access
        if not tokens:
            raise ApiForbiddenError(
                "Нет токенов для доступа к API",
                wb_user_cabinet=wb_access.wb_user_cabinet,
            )
        tokens = sorted(tokens, key=lambda x: x.expires, reverse=True)
        self._free_tokens = tokens
        current_token = self._free_tokens.pop()
        self._headers = Headers(current_token)
        self._shop_id = current_token.shop_id
        self.api_call_state: dict[str, dict[str, str]] = {}

    @property
    def headers(self) -> Headers:
        return self._headers

    @headers.setter
    def headers(self, value: Headers) -> None:
        self._headers = value

    @property
    def shop_id(self) -> str:
        return self.access.shop_id

    @staticmethod
    def chunks(lst: list[T], n: int) -> Generator[list[T], None, None]:
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    async def set_next_token(self) -> None:
        if self._free_tokens:
            self.headers = Headers(self._free_tokens.pop())
        else:
            wb_cabinet: WBCabinet | None = self.access.wb_cabinet
            if wb_cabinet is None:
                raise ApiForbiddenError(
                    "Нет WBCabinet для деактивации, метод set_next_token не может быть использован"
                )

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
                "Нет свободных токенов", wb_user_cabinet=self.access.wb_user_cabinet
            )
