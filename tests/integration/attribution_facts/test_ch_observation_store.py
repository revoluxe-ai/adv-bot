"""destructive_local ClickHouse tests for attribution observation store (Slice C)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
)
from app.modules.attribution_facts.domain.models import (
    AttributionScope,
    DateWindow,
)
from app.modules.attribution_facts.domain.observation_identity import (
    semantic_observation_id,
)
from app.modules.attribution_facts.ingest.pipeline import build_ingest_batch_from_raw_items
from app.modules.attribution_facts.membership.resolver import MembershipSnapshotResolver
from app.modules.attribution_facts.persistence.clickhouse_observation_repository import (
    ClickHouseAttributionObservationRepository,
)
from app.modules.attribution_facts.ports.campaign_settings_history import (
    HistorySnapshotView,
)
from app.modules.attribution_facts.readers.ch_attribution_facts_reader import (
    ChAttributionFactsReader,
)
from tests.support.destructive_clickhouse import ALLOWED_CH_DATABASE
from tests.support.rewrite_default_db_ch_client import rewriting_clickhouse_client

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "unit"
    / "attribution_facts"
    / "fixtures"
    / "fullstats_apps_nms_sample.json"
)
_OBS = f"{ALLOWED_CH_DATABASE}.attribution_fact_observations"
_RECON = f"{ALLOWED_CH_DATABASE}.attribution_day_reconciliation"
_DAY = date(2026, 9, 7)


class _History:
    async def snapshots_as_of(
        self,
        adv_setting_id: int,
        *,
        as_of_exclusive: datetime,
    ) -> tuple[HistorySnapshotView, ...]:
        return (
            HistorySnapshotView(
                snapshot_id="h1",
                observed_at=datetime(2026, 9, 6, 12, 0),  # noqa: DTZ001
                payload_json=json.dumps(
                    {"schema_version": 1, "campaign": {"nmids": [837395782, 111]}}
                ),
            ),
        )


async def _prepare_tables(client: object) -> None:
    ddl = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "clickhouse_migrations"
        / "008_create_attribution_facts.sql"
    ).read_text(encoding="utf-8")
    ddl = ddl.replace("default_db.", f"{ALLOWED_CH_DATABASE}.")
    for statement in ddl.split(";"):
        stmt = statement.strip()
        if stmt:
            await client.command(stmt)
    await client.command(f"TRUNCATE TABLE {_OBS}")
    await client.command(f"TRUNCATE TABLE {_RECON}")


async def _sample_batch() -> object:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    resolver = MembershipSnapshotResolver(
        shop_id="shop-ch",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=_History(),
        inventory_port=None,
    )
    return await build_ingest_batch_from_raw_items(
        shop_id="shop-ch",
        raw_items=(raw[0],),
        resolver=resolver,
    )


@pytest.mark.asyncio
async def test_migration_tables_and_latest_projection(clickhouse_client: object) -> None:
    await _prepare_tables(clickhouse_client)
    ch = rewriting_clickhouse_client(clickhouse_client)
    repo = ClickHouseAttributionObservationRepository(ch)
    reader = ChAttributionFactsReader(ch)
    batch = await _sample_batch()
    await repo.append_batch(batch)
    await repo.append_batch(batch)
    scope = AttributionScope(shop_id="shop-ch", physical_adv_ids=frozenset({39900256}))
    window = DateWindow(_DAY, _DAY)
    result = await reader.query(scope, window)
    assert len(result.facts) >= 1
    assert all(f.key.physical_adv_id == 39900256 for f in result.facts)
    assert result.coverage.status in (
        AttributionCoverageStatus.COMPLETE,
        AttributionCoverageStatus.PARTIAL,
    )


@pytest.mark.asyncio
async def test_correction_updates_latest_not_sums(clickhouse_client: object) -> None:
    await _prepare_tables(clickhouse_client)
    ch = rewriting_clickhouse_client(clickhouse_client)
    repo = ClickHouseAttributionObservationRepository(ch)
    reader = ChAttributionFactsReader(ch)
    batch_v1 = await _sample_batch()
    await repo.append_batch(batch_v1)
    fact = batch_v1.facts[0]
    from app.modules.attribution_facts.domain.models import (
        AttributionCommerceFact,
        AttributionFactKey,
        AttributionMetrics,
        ObservationProvenance,
    )

    newer_draft = AttributionCommerceFact(
        key=fact.key,
        metrics=AttributionMetrics(
            attributed_orders=99,
            attributed_gmv_rub=Decimal("123.45"),
            attributed_atc=fact.metrics.attributed_atc,
            attributed_units_shks=fact.metrics.attributed_units_shks,
        ),
        attribution_class=AttributionClass.DIRECT,
        provenance=ObservationProvenance(
            observation_id="pending",
            source_revision=fact.provenance.source_revision + 1,
            ingested_at=datetime(2026, 9, 8, 1, 0, tzinfo=UTC),
            membership_snapshot_id=fact.provenance.membership_snapshot_id,
        ),
    )
    newer = AttributionCommerceFact(
        key=newer_draft.key,
        metrics=newer_draft.metrics,
        attribution_class=newer_draft.attribution_class,
        provenance=ObservationProvenance(
            observation_id=semantic_observation_id(newer_draft),
            source_revision=newer_draft.provenance.source_revision,
            ingested_at=newer_draft.provenance.ingested_at,
            membership_snapshot_id=newer_draft.provenance.membership_snapshot_id,
        ),
    )
    from app.modules.attribution_facts.domain.ingest_models import AttributionIngestBatch

    batch_v2 = AttributionIngestBatch(
        shop_id=batch_v1.shop_id,
        facts=(newer,),
        reconciliations=batch_v1.reconciliations,
        coverage=batch_v1.coverage,
        used_raw_apps_nms=True,
        partial_membership_fallback=False,
        reason_codes=(),
    )
    await repo.append_batch(batch_v2)
    scope = AttributionScope(shop_id="shop-ch", physical_adv_ids=frozenset({39900256}))
    result = await reader.query(scope, DateWindow(_DAY, _DAY))
    match = next(f for f in result.facts if f.key == fact.key)
    assert match.metrics.attributed_orders == 99
    assert match.metrics.attributed_gmv_rub == Decimal("123.45")
