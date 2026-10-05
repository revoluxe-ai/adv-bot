"""Сигналы freshness из CH (не подмена coverage)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timezone
from typing import Any

from app.modules.ai_package_v1.domain.enums import FreshnessStatus
from app.modules.ai_package_v1.readers.sql_loader import load_sql
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

_FULL_ADV_QUERY = load_sql("freshness_full_adv_max_version")
_COMMON_QUERY = load_sql("freshness_common_stat_max_version")


def freshness_from_version_timestamp(
    max_version: float | None,
    period_end: date,
) -> FreshnessStatus:
    """
    Интерпретирует max(version) как freshness относительно конца периода.

    Не выводит ``Coverage.FULL`` — только ``FreshnessStatus``.

    Args:
        max_version: Unix timestamp из CH version или ``None``.
        period_end: Последний день export period.

    Returns:
        ``UNKNOWN`` при отсутствии данных; иначе FRESH/STALE по EOD UTC period_end.
    """
    if max_version is None:
        return FreshnessStatus.UNKNOWN
    last_write = datetime.fromtimestamp(max_version, tz=timezone.utc)
    period_eod = datetime.combine(
        period_end,
        datetime.max.time().replace(microsecond=0),
        tzinfo=timezone.utc,
    )
    if last_write >= period_eod:
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE


class ChExportFreshnessReader:
    """Read-only max(version) для полей freshness карточек датасетов."""

    async def max_full_adv_version(self, adv_ids: Sequence[int]) -> float | None:
        """Max version по ``default_db.full_adv_wb_stat`` для scoped adv_ids."""
        if not adv_ids:
            return None
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self._max_full_adv_version_with_client(
                    client, adv_ids=adv_ids
                )

    async def _max_full_adv_version_with_client(
        self,
        client: Any,
        *,
        adv_ids: Sequence[int],
    ) -> float | None:
        result = await client.query(
            _FULL_ADV_QUERY,
            parameters={"adv_ids": list(adv_ids)},
        )
        if not result.result_rows or result.result_rows[0][0] is None:
            return None
        return float(result.result_rows[0][0])

    async def max_common_stat_version(self, nmids: Sequence[int]) -> float | None:
        """Max version по ``default_db.wb_common_stat`` для scoped nmids."""
        if not nmids:
            return None
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self._max_common_stat_version_with_client(
                    client, nmids=nmids
                )

    async def _max_common_stat_version_with_client(
        self,
        client: Any,
        *,
        nmids: Sequence[int],
    ) -> float | None:
        result = await client.query(
            _COMMON_QUERY,
            parameters={"nmids": list(nmids)},
        )
        if not result.result_rows or result.result_rows[0][0] is None:
            return None
        return float(result.result_rows[0][0])
