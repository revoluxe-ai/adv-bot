"""ClickHouse reader: keyword_position_from_api stream (row-coherent max version)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, cast

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.readers.sql_loader import (
    load_keyword_sql,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol
from app.utils.click_house.client import get_clickhouse_client

_QUERY = load_keyword_sql("keyword_position_from_api")


@dataclass(frozen=True, slots=True)
class RawPositionRow:
    """Raw position observation from CH after row-coherent version pick."""

    nmid: int
    text: str
    stat_date: date
    version: int | None
    tuple_variants_at_max_version: int
    avr_position: float | None
    total_views: int | None
    orders: int | None


class ChKeywordPositionReader:
    """WB keyword position API read with version ms cutoff."""

    @property
    def query_text(self) -> str:
        return _QUERY

    async def fetch_rows(
        self,
        nmids: frozenset[int],
        position_first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawPositionRow]:
        if not nmids:
            return []
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_rows_with_client(
                    client,
                    nmids=nmids,
                    position_first_available=position_first_available,
                    cutoff=cutoff,
                )

    async def fetch_rows_with_client(
        self,
        client: ClickHouseClientProtocol,
        *,
        nmids: frozenset[int],
        position_first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawPositionRow]:
        result = await client.query(
            _QUERY,
            parameters={
                "nmids": list(nmids),
                "position_first_available": position_first_available.isoformat(),
                "package_cutoff_date": cutoff.package_cutoff_date.isoformat(),
                "cutoff_instant_ms": cutoff.cutoff_instant_ms,
            },
        )
        rows: list[RawPositionRow] = []
        for row in result.result_rows:
            parsed = _parse_row(tuple(row))
            if parsed is not None:
                rows.append(parsed)
        return rows


def _parse_row(row: tuple[Any, ...]) -> RawPositionRow | None:
    if len(row) < 6:
        return None
    variants = int(row[4] or 0)
    if variants > 1:
        return RawPositionRow(
            nmid=int(row[0]),
            text=str(row[1]),
            stat_date=_coerce_date(row[2]),
            version=_int_or_none(row[3]),
            tuple_variants_at_max_version=variants,
            avr_position=None,
            total_views=None,
            orders=None,
        )
    metrics = _unpack_position_tuple(row[5])
    return RawPositionRow(
        nmid=int(row[0]),
        text=str(row[1]),
        stat_date=_coerce_date(row[2]),
        version=_int_or_none(metrics[3]) if metrics[3] is not None else _int_or_none(row[3]),
        tuple_variants_at_max_version=variants,
        avr_position=_float_or_none(metrics[0]),
        total_views=_int_or_none(metrics[1]),
        orders=_int_or_none(metrics[2]),
    )


def _unpack_position_tuple(
    value: object,
) -> tuple[Any, Any, Any, Any]:
    if isinstance(value, tuple):
        seq = cast(tuple[Any, ...], value)
        if len(seq) >= 4:
            return (seq[0], seq[1], seq[2], seq[3])
    if isinstance(value, list):
        lst = cast(list[Any], value)
        if len(lst) >= 4:
            return (lst[0], lst[1], lst[2], lst[3])
    return (None, None, None, None)


def _coerce_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


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
