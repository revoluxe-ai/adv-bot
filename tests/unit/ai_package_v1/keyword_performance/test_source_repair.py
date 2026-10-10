"""SOURCE repair falsifiable fixtures (cap≠bid, decision, probe, position, coverage)."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    BidEvidenceStatus,
    CampaignSlotRole,
    DecisionEventClass,
    DecisionSourceKind,
    FinalBidSemantics,
    KeywordLegRole,
    NormQueryProvenance,
    SnapshotStatus,
)
from app.modules.ai_package_v1.keyword_performance.export.current_state import (
    compute_current_state,
)
from app.modules.ai_package_v1.keyword_performance.export.decision_assembler import (
    assemble_decision_rows,
)
from app.modules.ai_package_v1.keyword_performance.domain.coverage_assembler import (
    build_coverage_json,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import KeywordDailyRowV1
from app.modules.ai_package_v1.keyword_performance.export.position_assembler import (
    assemble_position_rows,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    BidDecisionAvailability,
    BidDecisionSourceStatus,
    ChBidDecisionProbe,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader import (
    ChBidDecisionReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    ChKeywordPositionReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_policy_reader import (
    CampaignPolicySnapshot,
)
from app.modules.ai_package_v1.keyword_performance.scope.dto import KeywordExportScope
from app.modules.ai_package_v1.keyword_performance.windows.position_engine import (
    compute_position_latest,
)
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    GENERATED_AT,
    MANIFEST_SHOP_ID,
    PERIOD,
    SHOP_ID,
    FakeKeywordDeps,
    build_fake_assembler,
    make_bid_decision_raw,
    make_daily_raw,
    make_position_raw,
    make_scope_row,
)

pytestmark = pytest.mark.unit


def test_cap_not_current_bid_evidence() -> None:
    """max_cpm policy cap exported separately; current_bid_evidence UNAVAILABLE."""
    row = KeywordDailyRowV1(
        shop_id="1",
        adv_setting_id=101,
        adv_id=111,
        leg_role=KeywordLegRole.AUTO,
        nmid=500,
        norm_query="q",
        date="2026-01-05",
        cpm=120.0,
    )
    policies = {
        101: CampaignPolicySnapshot(
            adv_setting_id=101,
            configured_max_cpm=500.0,
            bidder_active=True,
            campaign_active_status="active",
            strategy_status="MIN_CPO",
            min_target_position=10,
            target_position_mode="MIN_CPA",
        )
    }
    current = compute_current_state(
        [row],
        cutoff=PackageCutoff.from_generated_at("2026-01-10T12:00:00Z"),
        campaign_policies=policies,
    )
    state = current[0]
    assert state.configured_max_cpm == 500.0
    assert state.current_bid_evidence is None
    assert state.current_bid_evidence_status == BidEvidenceStatus.UNAVAILABLE
    assert state.observed_cpm == 120.0


def test_rebound_does_not_inherit_campaign_policy() -> None:
    """REBOUND_HISTORICAL rows must not carry current campaign policy as fact."""
    row = KeywordDailyRowV1(
        shop_id="1",
        adv_setting_id=101,
        adv_id=999,
        leg_role=KeywordLegRole.REBOUND_AUTO,
        nmid=500,
        norm_query="q",
        date="2026-01-05",
    )
    policies = {
        101: CampaignPolicySnapshot(
            adv_setting_id=101,
            configured_max_cpm=500.0,
            bidder_active=True,
            campaign_active_status="active",
            strategy_status="MIN_CPO",
            min_target_position=10,
            target_position_mode="MIN_CPA",
        )
    }
    current = compute_current_state([row], campaign_policies=policies)
    state = current[0]
    assert state.campaign_slot_role == CampaignSlotRole.REBOUND_HISTORICAL
    assert state.configured_max_cpm is None
    assert state.strategy_status is None


def test_decision_timeline_source_derived_event_class() -> None:
    """Exported DECISION rows carry source-derived event_class, not SQL filter."""
    raw = make_bid_decision_raw(cpm_curr=200.0)
    rows = assemble_decision_rows([raw], manifest_shop_id="1")
    assert rows[0].event_class == DecisionEventClass.DECISION
    assert rows[0].source_kind == DecisionSourceKind.RETROSPECTIVE_COMPUTED_CONTEXT
    assert rows[0].final_bid_semantics == (
        FinalBidSemantics.ANALYTICS_COMPUTED_NOT_VERIFIED_APPLIED
    )


def test_decision_latest_coherent_conflict_null() -> None:
    """Equal max version conflicting tuples → AMBIGUOUS null metrics."""
    raw = make_bid_decision_raw(variants=2)
    rows = assemble_decision_rows([raw], manifest_shop_id="1")
    assert rows[0].snapshot_status == SnapshotStatus.AMBIGUOUS
    assert rows[0].cpm_curr is None
    assert "SNAPSHOT_CONFLICT" in rows[0].row_coverage.reason_codes


@pytest.mark.asyncio
async def test_bid_probe_missing_required_column_unsupported() -> None:
    """Missing required column → UNSUPPORTED with explicit missing list."""
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=MagicMock(result_rows=[("adv_id",), ("nmid",)])
    )
    probe = ChBidDecisionProbe()
    result = await probe.probe_with_client(client, adv_ids=frozenset({111}))
    assert result.status == BidDecisionSourceStatus.UNSUPPORTED
    assert "norm_query" in result.missing_required_columns


@pytest.mark.asyncio
async def test_bid_probe_query_failure_failed() -> None:
    """Schema OK but sample query throws → FAILED."""
    client = AsyncMock()

    async def _query(sql: str, parameters: object = None) -> MagicMock:
        if "system.columns" in sql:
            return MagicMock(
                result_rows=[(c,) for c in ChBidDecisionProbe().required_columns]
            )
        raise RuntimeError("CH down")

    client.query = AsyncMock(side_effect=_query)
    probe = ChBidDecisionProbe()
    result = await probe.probe_with_client(
        client, adv_ids=frozenset({111}), cutoff=PackageCutoff.from_generated_at(GENERATED_AT)
    )
    assert result.status == BidDecisionSourceStatus.FAILED


@pytest.mark.asyncio
async def test_bid_decision_latest_sql_row_coherent_not_per_field_argmax() -> None:
    """Latest SQL uses tuple_variants_at_max_version, not separate argMax fields."""
    sql = ChBidDecisionReader().latest_query_text
    assert "tuple_variants_at_max_version" in sql
    assert "argMax(cpm_curr, version)" not in sql


def test_bid_decision_sql_max_version_not_nested_in_aggregates() -> None:
    """Outer max(version) alias must not be version (ClickHouse code 184)."""
    sql = ChBidDecisionReader().latest_query_text
    final_select = sql.rsplit("SELECT", maxsplit=1)[1]
    assert "FROM rows_at_max" in final_select
    assert "max(version) AS max_version" in final_select
    assert "max(version) AS version" not in sql
    after_uniq = sql.split("uniqExact(", maxsplit=1)[1]
    assert "max(version)" not in after_uniq
    decision_tuple = (
        "(cpm_curr, final_bid, decision_time, stats_max_timestamp, "
        "decision_source, version)"
    )
    assert decision_tuple in final_select
    assert "d.version = lv.max_version" in sql
    assert "decision_time <= {package_cutoff_instant:DateTime}" in sql
    assert "stats_max_timestamp <= {package_cutoff_instant:DateTime}" in sql


@pytest.mark.asyncio
async def test_position_api_future_version_excluded() -> None:
    """Position reader passes cutoff_instant_ms; future same-day version excluded."""
    cutoff = PackageCutoff.from_generated_at("2026-10-05T15:00:00Z")
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[]))
    reader = ChKeywordPositionReader()
    _ = await reader.fetch_rows_with_client(
        client,
        nmids=frozenset({500}),
        position_first_available=date(2026, 10, 1),
        cutoff=cutoff,
    )
    params = client.query.await_args.kwargs.get("parameters") or client.query.await_args[1][
        "parameters"
    ]
    assert params["cutoff_instant_ms"] == cutoff.cutoff_instant_ms
    assert "tuple_variants_at_max_version" in reader.query_text


def test_position_sql_max_version_not_nested_in_aggregates() -> None:
    """Outer max(version) alias must not be version (ClickHouse code 184)."""
    sql = ChKeywordPositionReader().query_text
    final_select = sql.rsplit("SELECT", maxsplit=1)[1]
    assert "FROM rows_at_max" in final_select
    assert "max(version) AS max_version" in final_select
    assert "max(version) AS version" not in sql
    after_uniq = sql.split("uniqExact(", maxsplit=1)[1]
    assert "max(version)" not in after_uniq
    assert "(avr_position, total_views, orders, version)" in final_select
    assert "s.version = lv.max_version" in sql
    assert "version <= {cutoff_instant_ms:UInt64}" in sql


@pytest.mark.asyncio
async def test_position_max_version_conflict_parsed_ambiguous() -> None:
    """Equal max version conflict → null position in reader parse."""
    cutoff = PackageCutoff.from_generated_at("2026-10-05T15:00:00Z")
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=MagicMock(
            result_rows=[
                (
                    500,
                    "query",
                    date(2026, 1, 3),
                    1_700_000_000_000,
                    2,
                    (3.0, 100, 1, 1_700_000_000_000),
                )
            ]
        )
    )
    reader = ChKeywordPositionReader()
    rows = await reader.fetch_rows_with_client(
        client,
        nmids=frozenset({500}),
        position_first_available=date(2026, 1, 1),
        cutoff=cutoff,
    )
    assert len(rows) == 1
    assert rows[0].tuple_variants_at_max_version == 2
    assert rows[0].avr_position is None


def test_position_norm_query_unproven_when_no_daily_match() -> None:
    """API-only rows keep norm_query null with NORMALIZATION_UNPROVEN."""
    raw = make_position_raw(text="raw query text")
    rows = assemble_position_rows(
        [raw],
        manifest_shop_id=MANIFEST_SHOP_ID,
        daily_norm_queries=frozenset(),
    )
    assert rows[0].norm_query is None
    assert rows[0].norm_query_provenance == NormQueryProvenance.NORMALIZATION_UNPROVEN


def test_position_latest_never_uses_old_when_latest_null() -> None:
    """Latest picker prefers newer date; ambiguous latest stays null."""
    from app.modules.ai_package_v1.keyword_performance.domain.enums import PositionType
    from app.modules.ai_package_v1.keyword_performance.domain.models import (
        KeywordPositionRowV1,
    )

    older = KeywordPositionRowV1(
        shop_id="1",
        nmid=500,
        source_query_text="q",
        date="2026-01-01",
        position_type=PositionType.WB_KEYWORD_POSITION_API,
        source_version=100,
        avr_position=10.0,
        source="keyword_position_from_api",
    )
    newer_null = KeywordPositionRowV1(
        shop_id="1",
        nmid=500,
        source_query_text="q",
        date="2026-01-05",
        position_type=PositionType.WB_KEYWORD_POSITION_API,
        source_version=200,
        avr_position=None,
        snapshot_status=SnapshotStatus.AMBIGUOUS,
        source="keyword_position_from_api",
    )
    latest = compute_position_latest([older, newer_null])
    assert latest[0].observation_date == "2026-01-05"
    assert latest[0].avr_position is None


def test_per_metric_identity_day_coverage() -> None:
    """Coverage uses unique identity×day cohort, not raw row count."""
    daily = [
        KeywordDailyRowV1(
            shop_id="1",
            adv_id=111,
            leg_role=KeywordLegRole.AUTO,
            nmid=500,
            norm_query="q",
            date="2026-01-01",
            views=10,
        ),
        KeywordDailyRowV1(
            shop_id="1",
            adv_id=111,
            leg_role=KeywordLegRole.AUTO,
            nmid=500,
            norm_query="q",
            date="2026-01-02",
            views=None,
        ),
    ]
    scope = KeywordExportScope(
        rows=(),
        assignments=(),
        all_adv_ids=frozenset({111}),
        all_nmids=frozenset({500}),
        reason_codes=frozenset(),
    )
    doc = build_coverage_json(
        scope=scope,
        cutoff=PackageCutoff.from_generated_at(GENERATED_AT),
        daily_first=date(2026, 1, 1),
        daily_last=date(2026, 1, 2),
        position_first=None,
        position_last=None,
        daily_rows=daily,
        position_rows=[],
        bid_decision=BidDecisionAvailability(status=BidDecisionSourceStatus.UNSUPPORTED),
        reason_codes=frozenset(),
    )
    views_cov = doc["datasets"]["keyword_daily"]["metric_coverage"]["views"]
    assert views_cov["requested"] == 2
    assert views_cov["observed"] == 1
    assert views_cov["missing"] == 1


@pytest.mark.asyncio
async def test_position_bounds_reader_failure_returns_none_bounds() -> None:
    """Position bounds query failure → (None, None) without crashing export."""
    from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
        ChKeywordBoundsReader,
    )

    reader = ChKeywordBoundsReader()
    with patch.object(
        reader,
        "fetch_position_bounds_with_client",
        side_effect=RuntimeError("missing table"),
    ):
        bounds = await reader.fetch_position_bounds(
            frozenset({500}),
            cutoff=PackageCutoff.from_generated_at(GENERATED_AT),
        )
    assert bounds.first_available is None
    assert bounds.last_available is None


@pytest.mark.asyncio
async def test_position_source_unavailable_coverage_reason() -> None:
    """When nmids scoped but position bounds absent → POSITION_SOURCE_UNAVAILABLE."""
    from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
        SourceBounds,
    )

    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row()],
        overlap={111: [(SHOP_ID, 101)], 222: [(SHOP_ID, 101)]},
        daily_raw=[make_daily_raw()],
        position_bounds=SourceBounds(None, None),
    )
    result = await build_fake_assembler(deps).assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=PERIOD,
        generated_at=GENERATED_AT,
    )
    coverage = next(p for p in result.payloads if p.dataset_id == "keyword_coverage")
    doc = json.loads(coverage.content.decode("utf-8"))
    assert "POSITION_SOURCE_UNAVAILABLE" in doc["reason_codes"]


@pytest.mark.asyncio
async def test_assembler_exports_decision_timeline_and_position_windows() -> None:
    """Integration: decision timeline + position windows/latest payloads present."""
    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row()],
        overlap={111: [(SHOP_ID, 101)], 222: [(SHOP_ID, 101)]},
        daily_raw=[make_daily_raw()],
        position_raw=[make_position_raw()],
        bid_decision_status=BidDecisionSourceStatus.AVAILABLE,
        bid_decision_raw=[make_bid_decision_raw(cpm_curr=188.0)],
        bid_decision_timeline=[
            make_bid_decision_raw(cpm_curr=180.0),
            make_bid_decision_raw(cpm_curr=188.0),
        ],
        policies={
            101: CampaignPolicySnapshot(
                adv_setting_id=101,
                configured_max_cpm=300.0,
                bidder_active=True,
                campaign_active_status="active",
                strategy_status="MIN_CPO",
                min_target_position=5,
                target_position_mode="MIN_CPA",
            )
        },
    )
    result = await build_fake_assembler(deps).assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=PERIOD,
        generated_at=GENERATED_AT,
    )
    ids = {p.dataset_id for p in result.payloads}
    assert "keyword_decisions" in ids
    assert "keyword_position_windows" in ids
    assert "keyword_position_current" in ids
    decisions = next(p for p in result.payloads if p.dataset_id == "keyword_decisions")
    lines = [ln for ln in decisions.content.decode("utf-8").strip().split("\n") if ln]
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["event_class"] == "DECISION"
    current = next(p for p in result.payloads if p.dataset_id == "keyword_current_state")
    cur_row = json.loads(current.content.decode("utf-8").strip())
    assert cur_row["configured_max_cpm"] == 300.0
    assert cur_row["current_bid_evidence"] is None
    assert cur_row["decision_cpm_curr"] == 188.0
