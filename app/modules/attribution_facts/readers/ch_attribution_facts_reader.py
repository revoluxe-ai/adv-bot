"""ClickHouse implementation of AttributionFactsReader (latest projection)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any, cast

from app.modules.attribution_facts.domain.coverage import (
    all_reconciliations_passed,
    evaluate_window_coverage,
)
from app.modules.attribution_facts.domain.enums import (
    AttributionCoverageStatus,
    AttributionReasonCode,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCoverage,
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
    DayReconciliationResult,
)
from app.modules.attribution_facts.persistence.rows import fact_from_ch_row
from app.modules.attribution_facts.ports.reader import AttributionFactsReader
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol

_OBS_TABLE = "default_db.attribution_fact_observations"
_RECON_TABLE = "default_db.attribution_day_reconciliation"

_LATEST_FACTS_SQL = f"""
SELECT
    shop_id,
    physical_adv_id,
    event_date,
    app_type,
    ordered_nm_id,
    argMax(source_family, (source_revision, ingested_at)) AS source_family,
    argMax(observation_id, (source_revision, ingested_at)) AS observation_id,
    argMax(source_revision, (source_revision, ingested_at)) AS source_revision,
    argMax(ingested_at, (source_revision, ingested_at)) AS ingested_at,
    argMax(attribution_class, (source_revision, ingested_at)) AS attribution_class,
    argMax(attributed_orders, (source_revision, ingested_at)) AS attributed_orders,
    argMax(attributed_gmv_rub, (source_revision, ingested_at)) AS attributed_gmv_rub,
    argMax(attributed_atc, (source_revision, ingested_at)) AS attributed_atc,
    argMax(attributed_units_shks, (source_revision, ingested_at)) AS attributed_units_shks,
    argMax(membership_snapshot_id, (source_revision, ingested_at)) AS membership_snapshot_id,
    argMax(partial_membership_fallback, (source_revision, ingested_at)) AS partial_membership_fallback
FROM {_OBS_TABLE}
WHERE shop_id = %(shop_id)s
  AND event_date >= %(start_date)s
  AND event_date <= %(end_date)s
  AND physical_adv_id IN %(physical_adv_ids)s
GROUP BY
    shop_id,
    physical_adv_id,
    event_date,
    app_type,
    ordered_nm_id
""".strip()

_LATEST_RECON_SQL = f"""
SELECT
    physical_adv_id,
    event_date,
    argMax(passed, (source_revision, ingested_at)) AS passed,
    argMax(nm_orders_sum, (source_revision, ingested_at)) AS nm_orders_sum,
    argMax(day_orders, (source_revision, ingested_at)) AS day_orders,
    argMax(nm_gmv_sum, (source_revision, ingested_at)) AS nm_gmv_sum,
    argMax(day_gmv_rub, (source_revision, ingested_at)) AS day_gmv_rub,
    argMax(unattributed_orders, (source_revision, ingested_at)) AS unattributed_orders,
    argMax(reason_codes, (source_revision, ingested_at)) AS reason_codes
FROM {_RECON_TABLE}
WHERE shop_id = %(shop_id)s
  AND event_date >= %(start_date)s
  AND event_date <= %(end_date)s
  AND physical_adv_id IN %(physical_adv_ids)s
GROUP BY shop_id, physical_adv_id, event_date
""".strip()


class ChAttributionFactsReader(AttributionFactsReader):
    """Production CH reader; schema hidden behind port types."""

    def __init__(self, client: ClickHouseClientProtocol) -> None:
        self._client = client

    async def query(
        self,
        scope: AttributionScope,
        window: DateWindow,
    ) -> AttributionQueryResult:
        adv_ids = sorted(scope.physical_adv_ids)
        if not adv_ids:
            return AttributionQueryResult(
                facts=(),
                coverage=AttributionCoverage(
                    status=AttributionCoverageStatus.NO_DATA,
                    reason_codes=(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING,),
                ),
                reconciliations=(),
            )
        params = {
            "shop_id": scope.shop_id,
            "start_date": window.start,
            "end_date": window.end,
            "physical_adv_ids": adv_ids,
        }
        ch = cast(Any, self._client)
        fact_result: Any = await ch.query(  # pyright: ignore[reportUnknownMemberType]
            _LATEST_FACTS_SQL, parameters=params
        )
        fact_rows = cast(
            Sequence[Sequence[object]],
            fact_result.result_rows,  # pyright: ignore[reportUnknownMemberType]
        )
        facts = tuple(fact_from_ch_row(row) for row in fact_rows)
        recon_result: Any = await ch.query(  # pyright: ignore[reportUnknownMemberType]
            _LATEST_RECON_SQL, parameters=params
        )
        recon_rows = cast(
            Sequence[Sequence[object]],
            recon_result.result_rows,  # pyright: ignore[reportUnknownMemberType]
        )
        reconciliations = tuple(
            _recon_from_row(scope.shop_id, row) for row in recon_rows
        )
        partial_fallback = any(bool(row[15]) for row in fact_rows) if fact_rows else False
        all_passed = all_reconciliations_passed(reconciliations)
        coverage = evaluate_window_coverage(
            has_any_facts=bool(facts),
            all_days_reconciled=all_passed and bool(reconciliations),
            partial_membership_fallback=partial_fallback,
            source_complete_through=window.end if all_passed and facts else None,
            window=window,
        )
        return AttributionQueryResult(
            facts=facts,
            coverage=coverage,
            reconciliations=reconciliations,
        )


def _recon_from_row(shop_id: str, row: Sequence[object]) -> DayReconciliationResult:
    (
        physical_adv_id,
        event_date,
        passed,
        nm_orders_sum,
        day_orders,
        nm_gmv_sum,
        day_gmv_rub,
        unattributed_orders,
        reason_codes_raw,
    ) = row
    reason_codes: tuple[AttributionReasonCode, ...] = ()
    if isinstance(reason_codes_raw, (list, tuple)):
        codes_seq = cast(Sequence[object], reason_codes_raw)
        reason_codes = tuple(
            AttributionReasonCode(str(item)) for item in codes_seq
        )
    return DayReconciliationResult(
        physical_adv_id=int(cast(int, physical_adv_id)),
        event_date=_as_date(event_date),
        passed=bool(int(cast(int, passed))),
        nm_orders_sum=int(cast(int, nm_orders_sum)),
        day_orders=int(cast(int, day_orders)),
        nm_gmv_sum=Decimal(str(nm_gmv_sum)),
        day_gmv_rub=Decimal(str(day_gmv_rub)),
        unattributed_orders=int(cast(int, unattributed_orders)),
        reason_codes=reason_codes,
    )


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
