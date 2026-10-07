"""ClickHouse reader: funnel/common stat только по main_nmid из scope."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.funnel_stat import FunnelStatRow
from app.modules.ai_package_v1.readers.sql_loader import load_sql
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

_QUERY = load_sql("funnel_by_nmids")


class ChFunnelReader:
    """Read-only срез ``default_db.wb_common_stat`` по whitelist nmids."""

    @property
    def query_text(self) -> str:
        """Текст SQL (для contract spy на ``default_db.`` qualification)."""
        return _QUERY

    async def fetch_rows(
        self,
        shop_id: str,
        nmids: Sequence[int],
        period: ExportPeriod,
    ) -> list[FunnelStatRow]:
        """
        Загружает funnel rows за период.

        Args:
            shop_id: Authoritative ``WBCabinet.shop_id`` (str), штамп на строках; SQL выбирает по nmid.
            nmids: Только ``main_nmid`` из export scope (не shop-wide).
            period: Границы периода.

        Returns:
            Пустой список, если ``nmids`` пуст.
        """
        if not nmids:
            return []
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_rows_with_client(
                    client, shop_id=shop_id, nmids=nmids, period=period
                )

    async def fetch_rows_with_client(
        self,
        client: Any,
        *,
        shop_id: str,
        nmids: Sequence[int],
        period: ExportPeriod,
    ) -> list[FunnelStatRow]:
        """
        Чтение funnel с переданным CH client (unit seam).

        Args:
            client: Async ClickHouse client.
            shop_id: Authoritative ``WBCabinet.shop_id`` (str), штамп на строках; SQL выбирает по nmid.
            nmids: Scoped main nmids.
            period: Период export.

        Returns:
            Строки nmid + date.
        """
        if not nmids:
            return []
        result = await client.query(
            _QUERY,
            parameters={
                "start_date": period.start.isoformat(),
                "end_date": period.end.isoformat(),
                "nmids": list(nmids),
            },
        )
        rows: list[FunnelStatRow] = []
        for row in result.result_rows:
            stat_date = _coerce_date(row[1])
            rows.append(
                FunnelStatRow(
                    shop_id=shop_id,
                    nmid=int(row[0]),
                    date=stat_date,
                    open_card=int(row[2] or 0),
                    add_to_cart=int(row[3] or 0),
                    orders=int(row[4] or 0),
                    orders_sum=int(row[5] or 0),
                    buy_outs=int(row[6] or 0),
                )
            )
        return rows


def _coerce_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    date_getter = getattr(value, "date", None)
    if callable(date_getter):
        converted = date_getter()
        if isinstance(converted, date):
            return converted
    return date.fromisoformat(str(value)[:10])
