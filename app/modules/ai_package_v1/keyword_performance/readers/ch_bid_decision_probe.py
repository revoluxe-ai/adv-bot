"""Read-only CH probe for bid_decision_log table/column availability."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol
from app.utils.click_house.client import get_clickhouse_client

_REQUIRED_COLUMNS = frozenset(
    {"adv_id", "nmid", "norm_query", "cpm_curr", "decision_time", "version"}
)
_OPTIONAL_COLUMNS = frozenset(
    {"final_bid", "stats_max_timestamp", "decision_source"}
)
_PROBED_COLUMNS = _REQUIRED_COLUMNS | _OPTIONAL_COLUMNS | frozenset({"event_class"})

_SCHEMA_SQL = """
SELECT name
FROM system.columns
WHERE database = 'default_db'
  AND table = 'bid_decision_log'
  AND name IN (
    'adv_id', 'nmid', 'norm_query', 'cpm_curr', 'decision_time',
    'version', 'final_bid', 'stats_max_timestamp', 'decision_source', 'event_class'
  )
"""

_SAMPLE_SQL = """
SELECT 1
FROM default_db.bid_decision_log
WHERE adv_id IN {adv_ids:Array(Int32)}
  AND decision_time <= {package_cutoff_instant:DateTime}
  AND (
      stats_max_timestamp IS NULL
      OR stats_max_timestamp <= {package_cutoff_instant:DateTime}
  )
LIMIT 1
"""


class BidDecisionSourceStatus(StrEnum):
    """Scoped bid_decision_log availability for coverage.json."""

    UNSUPPORTED = "UNSUPPORTED"
    AVAILABLE_EMPTY = "AVAILABLE_EMPTY"
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class BidDecisionAvailability:
    """Probe outcome: schema support, per-column presence, scoped rows."""

    status: BidDecisionSourceStatus
    present_columns: frozenset[str] = frozenset()
    missing_required_columns: frozenset[str] = frozenset()
    missing_optional_columns: frozenset[str] = frozenset()
    has_native_event_class: bool = False


class ChBidDecisionProbe:
    """Probe default_db.bid_decision_log schema and scoped row presence."""

    @property
    def required_columns(self) -> frozenset[str]:
        return _REQUIRED_COLUMNS

    @property
    def optional_columns(self) -> frozenset[str]:
        return _OPTIONAL_COLUMNS

    async def probe(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff | None = None
    ) -> BidDecisionAvailability:
        """Return structured availability; distinguish empty vs unsupported vs failed."""
        if not adv_ids:
            return BidDecisionAvailability(status=BidDecisionSourceStatus.UNSUPPORTED)
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.probe_with_client(
                    client, adv_ids=adv_ids, cutoff=cutoff
                )

    async def probe_with_client(
        self,
        client: ClickHouseClientProtocol,
        *,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff | None = None,
    ) -> BidDecisionAvailability:
        """Client-injectable probe for unit tests."""
        try:
            schema = await client.query(_SCHEMA_SQL)
        except Exception:
            return BidDecisionAvailability(status=BidDecisionSourceStatus.FAILED)
        present = {str(row[0]) for row in schema.result_rows}
        missing_required = _REQUIRED_COLUMNS - present
        if missing_required:
            return BidDecisionAvailability(
                status=BidDecisionSourceStatus.UNSUPPORTED,
                present_columns=frozenset(present & _PROBED_COLUMNS),
                missing_required_columns=frozenset(missing_required),
                missing_optional_columns=frozenset(_OPTIONAL_COLUMNS - present),
                has_native_event_class="event_class" in present,
            )
        missing_optional = _OPTIONAL_COLUMNS - present
        instant = (
            cutoff.package_cutoff_instant.strftime("%Y-%m-%d %H:%M:%S")
            if cutoff is not None
            else "2999-12-31 23:59:59"
        )
        try:
            sample = await client.query(
                _SAMPLE_SQL,
                parameters={
                    "adv_ids": list(adv_ids),
                    "package_cutoff_instant": instant,
                },
            )
        except Exception:
            return BidDecisionAvailability(
                status=BidDecisionSourceStatus.FAILED,
                present_columns=frozenset(present & _PROBED_COLUMNS),
                missing_required_columns=frozenset(),
                missing_optional_columns=frozenset(missing_optional),
                has_native_event_class="event_class" in present,
            )
        if not sample.result_rows:
            return BidDecisionAvailability(
                status=BidDecisionSourceStatus.AVAILABLE_EMPTY,
                present_columns=frozenset(present & _PROBED_COLUMNS),
                missing_required_columns=frozenset(),
                missing_optional_columns=frozenset(missing_optional),
                has_native_event_class="event_class" in present,
            )
        return BidDecisionAvailability(
            status=BidDecisionSourceStatus.AVAILABLE,
            present_columns=frozenset(present & _PROBED_COLUMNS),
            missing_required_columns=frozenset(),
            missing_optional_columns=frozenset(missing_optional),
            has_native_event_class="event_class" in present,
        )

    async def is_available(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff | None = None
    ) -> bool:
        """Legacy bool seam: True only when status is AVAILABLE."""
        result = await self.probe(adv_ids, cutoff)
        return result.status == BidDecisionSourceStatus.AVAILABLE
