"""ClickHouse append-only attribution observation repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from app.modules.attribution_facts.domain.ingest_models import AttributionIngestBatch
from app.modules.attribution_facts.persistence.rows import (
    observation_rows_from_batch,
    reconciliation_rows_from_batch,
)
from app.modules.attribution_facts.ports.observation_writer import (
    AttributionObservationWriter,
)
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol

_OBS_TABLE = "default_db.attribution_fact_observations"
_RECON_TABLE = "default_db.attribution_day_reconciliation"

_OBS_COLUMNS = (
    "shop_id",
    "physical_adv_id",
    "event_date",
    "app_type",
    "ordered_nm_id",
    "source_family",
    "observation_id",
    "source_revision",
    "ingested_at",
    "attribution_class",
    "attributed_orders",
    "attributed_gmv_rub",
    "attributed_atc",
    "attributed_units_shks",
    "membership_snapshot_id",
    "partial_membership_fallback",
)

_RECON_COLUMNS = (
    "shop_id",
    "physical_adv_id",
    "event_date",
    "passed",
    "nm_orders_sum",
    "day_orders",
    "nm_gmv_sum",
    "day_gmv_rub",
    "unattributed_orders",
    "reason_codes",
    "source_revision",
    "ingested_at",
)


class ClickHouseAttributionObservationRepository(AttributionObservationWriter):
    """INSERT-only repository; latest projection via reader argMax queries."""

    def __init__(self, client: ClickHouseClientProtocol) -> None:
        self._client = client

    async def append_batch(self, batch: AttributionIngestBatch) -> None:
        ch = cast(Any, self._client)
        obs_rows = observation_rows_from_batch(batch)
        if obs_rows:
            obs_rows = await self._filter_new_observations(obs_rows)
            if obs_rows:
                await ch.insert(
                    _OBS_TABLE,
                    cast(list[list[Any]], [list(row) for row in obs_rows]),
                    column_names=list(_OBS_COLUMNS),
                )
        recon_rows = reconciliation_rows_from_batch(batch)
        if recon_rows:
            await ch.insert(
                _RECON_TABLE,
                cast(list[list[Any]], [list(row) for row in recon_rows]),
                column_names=list(_RECON_COLUMNS),
            )

    async def _filter_new_observations(
        self,
        rows: Sequence[tuple[object, ...]],
    ) -> list[tuple[object, ...]]:
        observation_ids = [str(row[6]) for row in rows]
        if not observation_ids:
            return []
        query = f"""
SELECT observation_id
FROM {_OBS_TABLE}
WHERE shop_id = %(shop_id)s
  AND observation_id IN %(observation_ids)s
""".strip()
        shop_id = str(rows[0][0])
        result: Any = await ch.query(  # pyright: ignore[reportUnknownMemberType]
            query,
            parameters={
                "shop_id": shop_id,
                "observation_ids": observation_ids,
            },
        )
        result_rows = cast(
            Sequence[Sequence[object]],
            result.result_rows,  # pyright: ignore[reportUnknownMemberType]
        )
        existing = {str(row[0]) for row in result_rows}
        return [row for row in rows if str(row[6]) not in existing]
