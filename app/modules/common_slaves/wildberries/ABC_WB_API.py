import logging
import os
from abc import ABC
from collections import defaultdict
from typing import TYPE_CHECKING

from aiohttp import ClientSession

from app.core.wb_api.exceptions import ApiForbiddenError, NO_FREE_TOKENS_MESSAGE
from app.core.wb_api.token_rotation import sort_tokens_write_first
from app.modules.token_monitoring.models import NotificationType
from app.modules.token_monitoring.services.cabinet_status_service import (
    deactivate_cabinet_atomic_with_user_trackers,
)
from .models.wb_cabinet import WBCabinet

if TYPE_CHECKING:
    from .models import WBToken

__all__ = ["Headers"]

if TYPE_CHECKING:
    from .super_cabinet_manager import WBCabinetAccess

logger = logging.getLogger(__name__)


class WbRequestApiMixin(ABC):
    pass


class Headers:
    def __init__(self, token: "WBToken"):
        self.current_token: WBToken = token

    @property
    def standart(self) -> dict[str, str]:
        return {"Authorization": self.current_token.api_key}


# TODO: АРХИТЕКТУРНАЯ ПРОБЛЕМА - Дублирование базовых классов API [СРЕДНИЙ ПРИОРИТЕТ]
# Существует два похожих базовых класса: ABC_WB_API и BaseAPI (app/core/wb_api/base.py)
# Нужно провести рефакторинг для объединения или четкого разделения ответственности
# Дата: 04.09.2025
class ABC_WB_API(WbRequestApiMixin): # noqa
    current_path = os.path.dirname(os.path.abspath(__file__))
    ORDERS_REPORTS_FOLDER = os.path.join(current_path, "WB_orders_reports")
    DISCOUNT_REPORTS_FOLDER = os.path.join(current_path, "WB_discount_reports")
    DB_NAME = os.path.join(current_path, "stoks_from_site.db")
    _single_adv_files = os.path.join(current_path, "singe_adv_files")
    _single_advs_report = os.path.join(current_path, "single_advs_report.csv")

    def __init__(self, wb_access: "WBCabinetAccess", session: ClientSession) -> None:
        tokens: list[WBToken] = wb_access.tokens
        self.access = wb_access
        wb_cabinet: WBCabinet | None = wb_access.wb_cabinet
        self.wb_cabinet = wb_cabinet
        assert wb_cabinet
        if not tokens:
            raise ApiForbiddenError(
                "Нет токенов для доступа к API",
                wb_user_cabinet=wb_access.wb_user_cabinet,
            )
        tokens = sort_tokens_write_first(tokens)
        self._free_tokens = tokens
        current_token = self._free_tokens[0]
        self._current_token = current_token
        self.headers = Headers(current_token)
        shop_id = current_token.shop_id
        self._shop_id = shop_id
        self.shop_id = shop_id
        self.session: ClientSession = session
        self._bad_tokens_original_ids: dict[str, set[int]] = defaultdict(set)

    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    async def set_next_token(self, method_name: str) -> None:
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
