"""ClickHouse reader: row-coherent daily facts from clusters_adv_stats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, cast

from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.readers.sql_loader import (
    load_keyword_sql,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

_QUERY = load_keyword_sql("keyword_daily_from_clusters")


@dataclass(frozen=True, slots=True)
class RawDailySnapshotRow:
    """Raw CH row before assembler enrichment."""

    adv_id: int
    nmid: int
    norm_query: str
    stat_date: date
    last_snapshot_ts: datetime | None
    snapshot_variants_at_max_ts: int
    views: int | None
    clicks: int | None
    add_to_cart: int | None
    orders: int | None
    spend: float | None
    cpm: float | None
    cpc: float | None
    avr_pos: float | None
    ctr: float | None


class ChKeywordDailyReader:
    """Bounded batch fetch daily facts (no per-key N+1)."""

    @property
    def query_text(self) -> str:
        return _QUERY

    async def fetch_rows(
        self,
        adv_ids: frozenset[int],
        first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawDailySnapshotRow]:
        """Load all daily rows for adv_id superset in one query."""
        if not adv_ids:
            return []
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_rows_with_client(
                    client,
                    adv_ids=adv_ids,
                    first_available=first_available,
                    cutoff=cutoff,
                )

    async def fetch_rows_with_client(
        self,
        client: ClickHouseClientProtocol,
        *,
        adv_ids: frozenset[int],
        first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawDailySnapshotRow]:
        """Fetch daily rows batched by UTC year partition."""
        rows: list[RawDailySnapshotRow] = []
        for year in range(first_available.year, cutoff.package_cutoff_date.year + 1):
            batch_start = date(year, 1, 1)
            if batch_start < first_available:
                batch_start = first_available
            batch_end = date(year, 12, 31)
            if batch_end > cutoff.package_cutoff_date:
                batch_end = cutoff.package_cutoff_date
            if batch_start > batch_end:
                continue
            result = await client.query(
                _QUERY,
                parameters={
                    "adv_ids": list(adv_ids),
                    "first_available": batch_start.isoformat(),
                    "package_cutoff_date": batch_end.isoformat(),
                    "package_cutoff_instant": cutoff.package_cutoff_instant.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                },
            )
            for row in result.result_rows:
                parsed = _parse_row(tuple(row))
                if parsed is not None:
                    rows.append(parsed)
        return rows


def _parse_row(row: tuple[Any, ...]) -> RawDailySnapshotRow | None:
    variants = int(row[5] or 0)
    tuple_val = row[6]
    if variants > 1:
        return RawDailySnapshotRow(
            adv_id=int(row[0]),
            nmid=int(row[1]),
            norm_query=str(row[2]),
            stat_date=_coerce_date(row[3]),
            last_snapshot_ts=_coerce_datetime(row[4]),
            snapshot_variants_at_max_ts=variants,
            views=None,
            clicks=None,
            add_to_cart=None,
            orders=None,
            spend=None,
            cpm=None,
            cpc=None,
            avr_pos=None,
            ctr=None,
        )
    metrics = _unpack_tuple(tuple_val)
    return RawDailySnapshotRow(
        adv_id=int(row[0]),
        nmid=int(row[1]),
        norm_query=str(row[2]),
        stat_date=_coerce_date(row[3]),
        last_snapshot_ts=_coerce_datetime(row[4]),
        snapshot_variants_at_max_ts=variants,
        views=_int_or_none(metrics[0]),
        clicks=_int_or_none(metrics[1]),
        add_to_cart=_int_or_none(metrics[2]),
        orders=_int_or_none(metrics[3]),
        spend=_float_or_none(metrics[4]),
        cpm=_float_or_none(metrics[5]),
        cpc=_float_or_none(metrics[6]),
        avr_pos=_float_or_none(metrics[7]),
        ctr=_float_or_none(metrics[8]),
    )


def _unpack_tuple(value: object) -> tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any]:
    if isinstance(value, (list, tuple)):
        seq = cast(list[Any] | tuple[Any, ...], value)
        padded: list[Any] = list(seq)
        while len(padded) < 9:
            padded.append(None)
        return (
            padded[0],
            padded[1],
            padded[2],
            padded[3],
            padded[4],
            padded[5],
            padded[6],
            padded[7],
            padded[8],
        )
    return (None, None, None, None, None, None, None, None, None)


def _coerce_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def _coerce_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if not text:
        return None
    return datetime.fromisoformat(text.replace(" ", "T"))


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    return None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None
