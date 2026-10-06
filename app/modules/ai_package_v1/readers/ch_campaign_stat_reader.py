"""ClickHouse reader: campaign full stat по scoped adv_id (отдельные Auto/Search)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from app.modules.ai_package_v1.domain.campaign_stat import CampaignStatRow
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.readers.sql_loader import load_sql
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

_QUERY = load_sql("campaign_full_stat_by_adv_ids")


class ChCampaignStatReader:
    """Read-only срез ``default_db.full_adv_wb_stat`` на зерне adv_id + date."""

    @property
    def query_text(self) -> str:
        """Текст SQL (для contract spy на ``default_db.`` qualification)."""
        return _QUERY

    async def fetch_rows(
        self,
        shop_id: str,
        adv_ids: Sequence[int],
        period: ExportPeriod,
    ) -> list[CampaignStatRow]:
        """
        Загружает строки campaign stat за период.

        Args:
            shop_id: Authoritative ``WBCabinet.shop_id`` (str), штамп на строках; SQL выбирает по adv_id.
            adv_ids: Scoped adv_id (auto и search раздельно).
            period: Границы периода export.

        Returns:
            Пустой список, если ``adv_ids`` пуст.
        """
        if not adv_ids:
            return []
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_rows_with_client(
                    client, shop_id=shop_id, adv_ids=adv_ids, period=period
                )

    async def fetch_rows_with_client(
        self,
        client: Any,
        *,
        shop_id: str,
        adv_ids: Sequence[int],
        period: ExportPeriod,
    ) -> list[CampaignStatRow]:
        """
        То же чтение с переданным CH client (unit/integration seam).

        Args:
            client: Async ClickHouse client с ``query(sql, parameters=...)``.
            shop_id: Authoritative shop id (str), не фильтр SQL.
            adv_ids: Scoped adv_id.
            period: Период export.

        Returns:
            Строки на зерне campaign_id + date.
        """
        if not adv_ids:
            return []
        result = await client.query(
            _QUERY,
            parameters={
                "start_date": period.start.isoformat(),
                "end_date": period.end.isoformat(),
                "adv_ids": list(adv_ids),
            },
        )
        rows: list[CampaignStatRow] = []
        for row in result.result_rows:
            stat_date = _coerce_date(row[1])
            rows.append(
                CampaignStatRow(
                    shop_id=shop_id,
                    campaign_id=int(row[0]),
                    date=stat_date,
                    views=int(row[2] or 0),
                    clicks=int(row[3] or 0),
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
