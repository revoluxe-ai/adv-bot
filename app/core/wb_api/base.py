import logging
import typing
from collections import defaultdict
from collections.abc import Generator
from typing import TypeVar

from aiohttp import ClientSession

from .exceptions import ApiForbiddenError, NO_FREE_TOKENS_MESSAGE
from .token_rotation import sort_tokens_write_first

from app.modules.token_monitoring.models import NotificationType
from app.modules.token_monitoring.services.cabinet_status_service import (
    deactivate_cabinet_atomic_with_user_trackers,
)

if typing.TYPE_CHECKING:
    from ...modules.common_slaves.wildberries.ABC_WB_API import Headers
    from ...modules.common_slaves.wildberries.super_cabinet_manager import (
        WBCabinetAccess,
    )
    from ...modules.common_slaves.wildberries.models import WBToken

from ...modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

logger = logging.getLogger(__name__)

T = TypeVar("T")


# !!!устаревший класс, новый тут app/core/wb_api/base_wb_api_v2.py!!!


# TODO: АРХИТЕКТУРНАЯ ПРОБЛЕМА - Дублирование базовых классов API [СРЕДНИЙ ПРИОРИТЕТ]
# Существует два похожих базовых класса: BaseAPI и ABC_WB_API (app/modules/common_slaves/wildberries/ABC_WB_API.py)
# Нужно провести рефакторинг для объединения или четкого разделения ответственности
# Дата: 04.09.2025
class BaseAPI:
    HOST = "wildberries.ru"

    def __init__(
        self, wb_access: "WBCabinetAccess", client_session: ClientSession
    ) -> None:
        from ...modules.common_slaves.wildberries.ABC_WB_API import Headers

        tokens: list[WBToken] = wb_access.tokens
        self.access: WBCabinetAccess = wb_access
        if not tokens:
            raise ApiForbiddenError(
                "Нет токенов для доступа к API",
                wb_user_cabinet=wb_access.wb_user_cabinet,
            )
        tokens = sort_tokens_write_first(tokens)
        self._free_tokens = tokens
        current_token = self._free_tokens[0]
        self._current_token = current_token
        self._headers = Headers(current_token)
        self._shop_id = current_token.shop_id
        self.api_call_state: dict[str, dict[str, str]] = {}
        self.wb_cabinet = wb_access.wb_cabinet
        self.session: ClientSession = client_session
        self._bad_tokens_original_ids: dict[str, set[int]] = defaultdict(set)

    @property
    def headers(self) -> "Headers":
        return self._headers

    @headers.setter
    def headers(self, value: "Headers") -> None:
        self._headers = value

    @property
    def shop_id(self) -> str:
        return self.access.shop_id

    @staticmethod
    def chunks(lst: list[T], n: int) -> Generator[list[T], None, None]:
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    async def set_next_token(self, method_name: str) -> None:
        from ...modules.common_slaves.wildberries.ABC_WB_API import Headers

        current_token_original_id = self._current_token.id
        self._bad_tokens_original_ids[method_name].add(current_token_original_id)

        all_bad_token_original_ids: set[int] = self._bad_tokens_original_ids[
            method_name
        ]

        free_tokens = [
            token
            for token in self._free_tokens
            if token.id not in all_bad_token_original_ids
        ]

        if free_tokens:
            self._current_token = free_tokens[0]
            self.headers = Headers(self._current_token)
        else:
            wb_cabinet: WBCabinet | None = self.access.wb_cabinet
            if wb_cabinet is None:
                raise ApiForbiddenError(
                    "Нет WBCabinet для деактивации, метод set_next_token не может быть использован"
                )

            try:
                shop_id_str = str(wb_cabinet.shop_id)
                await deactivate_cabinet_atomic_with_user_trackers(
                    shop_id_str,
                    notification_type=NotificationType.TOKEN_DEACTIVATED.value,
                )
            except Exception as e:
                logger.error(
                    f"Ошибка при отключении кабинета {wb_cabinet.shop_id}: {e}",
                    exc_info=True,
                )
                raise e
            raise ApiForbiddenError(
                NO_FREE_TOKENS_MESSAGE, wb_user_cabinet=self.access.wb_user_cabinet
            )
