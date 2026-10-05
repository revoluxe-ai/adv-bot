"""ClickHouse reader: bid_decision_log timeline + row-coherent latest per identity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    DecisionEventClass,
    DecisionSourceKind,
)
from app.modules.ai_package_v1.keyword_performance.readers.sql_loader import (
    load_keyword_sql,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol
from app.utils.click_house.client import get_clickhouse_client

_LATEST_QUERY = load_keyword_sql("bid_decision_latest")
_TIMELINE_QUERY = load_keyword_sql("bid_decision_timeline")


@dataclass(frozen=True, slots=True)
class RawBidDecisionRow:
    """Raw CH decision row before export labeling."""

    adv_id: int
    nmid: int
    norm_query: str
    cpm_curr: float | None
    final_bid: float | None
    decision_time: datetime | None
    stats_max_timestamp: datetime | None
    decision_source: str | None
    version: int | None
    tuple_variants_at_max_version: int = 1
    event_class: DecisionEventClass = DecisionEventClass.DECISION
    source_kind: DecisionSourceKind = DecisionSourceKind.RETROSPECTIVE_COMPUTED_CONTEXT


class ChBidDecisionReader:
    """Read-only decisions for trusted adv_ids at package cutoff."""

    @property
    def latest_query_text(self) -> str:
        return _LATEST_QUERY

    @property
    def timeline_query_text(self) -> str:
        return _TIMELINE_QUERY

    async def fetch_latest_decisions(
        self,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        """Load row-coherent latest decision rows per campaign identity."""
        if not adv_ids:
            return []
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_latest_decisions_with_client(
                    client,
                    adv_ids=adv_ids,
                    cutoff=cutoff,
                )

    async def fetch_timeline(
        self,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        """Load all historical decision rows ≤ cutoff (timeline export)."""
        if not adv_ids:
            return []
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_timeline_with_client(
                    client,
                    adv_ids=adv_ids,
                    cutoff=cutoff,
                )

    async def fetch_latest_decisions_with_client(
        self,
        client: ClickHouseClientProtocol,
        *,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        """Client-injectable latest fetch for unit tests."""
        result = await client.query(
            _LATEST_QUERY,
            parameters={
                "adv_ids": list(adv_ids),
                "package_cutoff_instant": cutoff.package_cutoff_instant.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
        )
        rows: list[RawBidDecisionRow] = []
        for row in result.result_rows:
            parsed = _parse_latest_row(tuple(row))
            if parsed is not None:
                rows.append(parsed)
        return rows

    async def fetch_timeline_with_client(
        self,
        client: ClickHouseClientProtocol,
        *,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        """Client-injectable timeline fetch for unit tests."""
        result = await client.query(
            _TIMELINE_QUERY,
            parameters={
                "adv_ids": list(adv_ids),
                "package_cutoff_instant": cutoff.package_cutoff_instant.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
        )
        rows: list[RawBidDecisionRow] = []
        for row in result.result_rows:
            parsed = _parse_timeline_row(tuple(row))
            if parsed is not None:
                rows.append(parsed)
        return rows


def _parse_latest_row(row: tuple[Any, ...]) -> RawBidDecisionRow | None:
    if len(row) < 6:
        return None
    variants = int(row[4] or 0)
    if variants > 1:
        return RawBidDecisionRow(
            adv_id=int(row[0]),
            nmid=int(row[1]),
            norm_query=str(row[2]),
            cpm_curr=None,
            final_bid=None,
            decision_time=None,
            stats_max_timestamp=None,
            decision_source=None,
            version=_int_or_none(row[3]),
            tuple_variants_at_max_version=variants,
        )
    metrics = _unpack_decision_tuple(row[5])
    return RawBidDecisionRow(
        adv_id=int(row[0]),
        nmid=int(row[1]),
        norm_query=str(row[2]),
        cpm_curr=_float_or_none(metrics[0]),
        final_bid=_float_or_none(metrics[1]),
        decision_time=_coerce_datetime(metrics[2]),
        stats_max_timestamp=_coerce_datetime(metrics[3]),
        decision_source=str(metrics[4]) if metrics[4] is not None else None,
        version=_int_or_none(metrics[5]) if metrics[5] is not None else _int_or_none(row[3]),
        tuple_variants_at_max_version=variants,
    )


def _parse_timeline_row(row: tuple[Any, ...]) -> RawBidDecisionRow | None:
    if len(row) < 9:
        return None
    return RawBidDecisionRow(
        adv_id=int(row[0]),
        nmid=int(row[1]),
        norm_query=str(row[2]),
        cpm_curr=_float_or_none(row[3]),
        final_bid=_float_or_none(row[4]),
        decision_time=_coerce_datetime(row[5]),
        stats_max_timestamp=_coerce_datetime(row[6]),
        decision_source=str(row[7]) if row[7] is not None else None,
        version=_int_or_none(row[8]),
    )


def _unpack_decision_tuple(
    value: object,
) -> tuple[Any, Any, Any, Any, Any, Any]:
    if isinstance(value, tuple):
        seq = cast(tuple[Any, ...], value)
        if len(seq) >= 6:
            return (seq[0], seq[1], seq[2], seq[3], seq[4], seq[5])
    if isinstance(value, list):
        lst = cast(list[Any], value)
        if len(lst) >= 6:
            return (lst[0], lst[1], lst[2], lst[3], lst[4], lst[5])
    return (None, None, None, None, None, None)


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
