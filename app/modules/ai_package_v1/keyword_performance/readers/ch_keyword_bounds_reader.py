"""CH MIN/MAX bounds per source with package cutoff filters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.readers.sql_loader import (
    load_keyword_sql,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

_DAILY_BOUNDS = load_keyword_sql("keyword_history_bounds")
_POSITION_BOUNDS = load_keyword_sql("keyword_position_bounds")


@dataclass(frozen=True, slots=True)
class SourceBounds:
    """first_available / last_available for one CH source."""

    first_available: date | None
    last_available: date | None


class ChKeywordBoundsReader:
    """Per-source independent bounds discovery."""

    @property
    def daily_bounds_query(self) -> str:
        return _DAILY_BOUNDS

    @property
    def position_bounds_query(self) -> str:
        return _POSITION_BOUNDS

    async def fetch_daily_bounds(
        self,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> SourceBounds:
        """MIN/MAX date on clusters_adv_stats with cutoff filters."""
        if not adv_ids:
            return SourceBounds(None, None)
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_daily_bounds_with_client(
                    client, adv_ids, cutoff
                )

    async def fetch_daily_bounds_with_client(
        self,
        client: Any,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> SourceBounds:
        result = await client.query(
            _DAILY_BOUNDS,
            parameters={
                "adv_ids": list(adv_ids),
                "package_cutoff_date": cutoff.package_cutoff_date.isoformat(),
                "package_cutoff_instant": cutoff.package_cutoff_instant.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
        )
        if not result.result_rows:
            return SourceBounds(None, None)
        row = result.result_rows[0]
        first = _coerce_date(row[0])
        last = _clamp_last_available(_coerce_date(row[1]), cutoff)
        return SourceBounds(first, last)

    async def fetch_position_bounds(
        self,
        nmids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> SourceBounds:
        """Independent position bounds (version ms cutoff).

        Returns ``(None, None)`` on query failure so optional API stream stays
        UNSUPPORTED instead of crashing the export path.
        """
        if not nmids:
            return SourceBounds(None, None)
        try:
            async with anti_ch_crash_semaphore:
                async with get_clickhouse_client() as client:
                    return await self.fetch_position_bounds_with_client(
                        client, nmids, cutoff
                    )
        except Exception:
            return SourceBounds(None, None)

    async def fetch_position_bounds_with_client(
        self,
        client: Any,
        nmids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> SourceBounds:
        result = await client.query(
            _POSITION_BOUNDS,
            parameters={
                "nmids": list(nmids),
                "package_cutoff_date": cutoff.package_cutoff_date.isoformat(),
                "cutoff_instant_ms": cutoff.cutoff_instant_ms,
            },
        )
        if not result.result_rows:
            return SourceBounds(None, None)
        row = result.result_rows[0]
        first = _coerce_date(row[0])
        last = _clamp_last_available(_coerce_date(row[1]), cutoff)
        return SourceBounds(first, last)


def _clamp_last_available(last: date | None, cutoff: PackageCutoff) -> date | None:
    """Reader-side guard: CH MAX(date) must not exceed package_cutoff_date."""
    if last is None:
        return None
    if last > cutoff.package_cutoff_date:
        return None
    return last


def _coerce_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    if not text or text == "1970-01-01":
        return None
    return date.fromisoformat(text)
