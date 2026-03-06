from __future__ import annotations
import logging
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo

from app.core.di.wb_manager_hub import WBManagerHub
from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

from .clickhouse_common_stat_manager import ClickHouseCommonStatManager

logger = logging.getLogger(__name__)

class CommonSaleStatUpdater:
    def __init__(
        self,
        wb_manager_hub: WBManagerHub,
        clickhouse_manager: ClickHouseCommonStatManager,
    ) -> None:
        self._wb_manager_hub = wb_manager_hub
        self._clickhouse_manager = clickhouse_manager

    async def update_last_week_stats(self, complex_advs: list[ComplexAdv]) -> set[int]:
        if not complex_advs:
            return set()

        nmids: list[int] = sorted({adv.main_nmid for adv in complex_advs})
        if not nmids:
            return set()

        MSK = ZoneInfo("Europe/Moscow")
        today = datetime.now(MSK).date()
        start = today - timedelta(days=6)
        end = today

        all_rows: list[CommonSaleStatRow] = []

        for chunk in _chunked(nmids, size=20):
            try:
                rows = await self._wb_manager_hub.wb_data_manager.get_sales_funnel_products_history(
                    nmids=chunk,
                    start=start,
                    end=end,
                )
            except Exception as e:
                logger.exception('Ошибка обновления общей воронки')
                raise e

            all_rows.extend(rows)

        await self._clickhouse_manager.insert(all_rows)
        updated_nmids: set[int] = {row.nmid for row in all_rows}
        return updated_nmids


def _chunked(items: list[int], size: int) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


