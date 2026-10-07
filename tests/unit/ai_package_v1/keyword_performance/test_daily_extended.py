"""Extended daily/position/bid tests (S01,S04,S12,S22,S23,S27,S45,S47)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    CampaignSlotRole,
    PositionType,
)
from app.modules.ai_package_v1.keyword_performance.export.current_state import (
    compute_current_state,
)
from app.modules.ai_package_v1.keyword_performance.export.daily_assembler import (
    assemble_daily_rows,
)
from app.modules.ai_package_v1.keyword_performance.export.position_assembler import (
    assemble_position_rows,
)
from app.modules.ai_package_v1.keyword_performance.guards.forbidden_sources import (
    FORBIDDEN_MODULES,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader import (
    ChKeywordDailyReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    RawPositionRow,
)
from app.modules.ai_package_v1.keyword_performance.scope.adv_id_collector import (
    collect_keyword_export_scope,
)
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    MANIFEST_SHOP_ID,
    make_daily_raw,
    make_scope_row,
)

pytestmark = pytest.mark.unit


def _scope():
    row = make_scope_row()
    overlap = {111: [("1", 101)], 222: [("1", 101)]}
    return collect_keyword_export_scope([row], overlap)


def test_daily_grain_strict() -> None:
    """S01: strict grain fields preserved on daily row."""
    raw = make_daily_raw(adv_id=111, nmid=500, norm_query="kw")
    rows = assemble_daily_rows([raw], manifest_shop_id=MANIFEST_SHOP_ID, scope=_scope())
    row = rows[0]
    assert row.adv_id == 111
    assert row.nmid == 500
    assert row.norm_query == "kw"
    assert row.date == "2026-01-03"


def test_no_ui_pagination_bound() -> None:
    """S04: daily reader SQL has no LIMIT 7/30 pagination."""
    sql = ChKeywordDailyReader().query_text
    assert "LIMIT 7" not in sql
    assert "LIMIT 30" not in sql


def test_forbidden_ui_sql_path() -> None:
    """S12: UI daily history manager not in forbidden guard list as authority."""
    assert (
        "app.modules.wb_adv_updater.keyword_daily_history.keyword_daily_history_manager"
        in FORBIDDEN_MODULES
    )


def test_position_types_separate() -> None:
    """S23: position assembler tags API stream separately."""
    raw = RawPositionRow(
        nmid=500,
        text="query",
        stat_date=date(2026, 1, 3),
        version=1_700_000_000_000,
        tuple_variants_at_max_version=1,
        avr_position=3.5,
        total_views=100,
        orders=1,
    )
    rows = assemble_position_rows(
        [raw],
        manifest_shop_id=MANIFEST_SHOP_ID,
        daily_norm_queries=frozenset({(500, "2026-01-03", "query")}),
    )
    assert rows[0].position_type == PositionType.WB_KEYWORD_POSITION_API
    assert rows[0].source == "keyword_position_from_api"


def test_bid_cpm_distinct() -> None:
    """S27: current state keeps observed_cpm separate from configured bid evidence."""
    from app.modules.ai_package_v1.keyword_performance.domain.enums import KeywordLegRole
    from app.modules.ai_package_v1.keyword_performance.domain.models import KeywordDailyRowV1

    rows = [
        KeywordDailyRowV1(
            shop_id="1",
            adv_id=111,
            leg_role=KeywordLegRole.AUTO,
            nmid=500,
            norm_query="q",
            date="2026-01-05",
            cpm=120.0,
        )
    ]
    current = compute_current_state(rows, cutoff=PackageCutoff.from_generated_at("2026-01-10T12:00:00Z"))
    assert current[0].observed_cpm == 120.0
    assert current[0].current_bid_evidence is None
    assert current[0].decision_cpm_curr is None


def test_mv_not_campaign_current_state() -> None:
    """S47: rebound slot is REBOUND_HISTORICAL, not ACTIVE."""
    from app.modules.ai_package_v1.keyword_performance.domain.enums import KeywordLegRole
    from app.modules.ai_package_v1.keyword_performance.domain.models import KeywordDailyRowV1

    rows = [
        KeywordDailyRowV1(
            shop_id="1",
            adv_id=999,
            leg_role=KeywordLegRole.REBOUND_AUTO,
            nmid=500,
            norm_query="q",
            date="2026-01-05",
        )
    ]
    current = compute_current_state(rows)
    assert current[0].campaign_slot_role == CampaignSlotRole.REBOUND_HISTORICAL


@pytest.mark.asyncio
async def test_cutoff_excludes_future_bounds() -> None:
    """S45: reader batch end capped at package_cutoff_date."""
    from unittest.mock import AsyncMock, MagicMock

    cutoff = PackageCutoff.from_generated_at("2026-10-05T15:00:00Z")
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[]))
    reader = ChKeywordDailyReader()
    _ = await reader.fetch_rows_with_client(
        client,
        adv_ids=frozenset({111}),
        first_available=date(2026, 10, 1),
        cutoff=cutoff,
    )
    for call in client.query.await_args_list:
        params = call.kwargs.get("parameters") or call[1].get("parameters")
        assert params["package_cutoff_date"] <= "2026-10-05"


@pytest.mark.asyncio
async def test_cutoff_future_bounds_excluded_from_export_metadata() -> None:
    """S45: export metadata last_available excludes future CH bounds; legit rows kept."""
    import json
    from datetime import UTC

    from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
        SourceBounds,
    )
    from tests.unit.ai_package_v1.keyword_performance.conftest import (
        PERIOD,
        SHOP_ID,
        FakeKeywordDeps,
        build_fake_assembler,
        make_daily_raw,
        make_scope_row,
    )

    cutoff_generated_at = "2026-01-07T12:00:00Z"
    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row()],
        overlap={111: [(SHOP_ID, 101)], 222: [(SHOP_ID, 101)]},
        daily_raw=[
            make_daily_raw(
                stat_date=date(2026, 1, 5),
                last_snapshot_ts=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
                views=21,
            ),
            make_daily_raw(stat_date=date(2026, 3, 1), views=99),
        ],
        daily_bounds=SourceBounds(date(2026, 1, 1), date(2026, 3, 1)),
    )
    result = await build_fake_assembler(deps).assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=PERIOD,
        generated_at=cutoff_generated_at,
    )
    data_map = json.loads(
        next(p for p in result.payloads if p.dataset_id == "DATA_MAP").content.decode(
            "utf-8"
        )
    )
    assert data_map["keyword_history_bounds"]["daily_last_available"] == "2026-01-05"
    assert data_map["package_cutoff_date"] == "2026-01-07"
    coverage = json.loads(
        next(p for p in result.payloads if p.dataset_id == "keyword_coverage").content.decode(
            "utf-8"
        )
    )
    assert coverage["datasets"]["keyword_daily"]["last_available"] == "2026-01-05"
    daily = next(p for p in result.payloads if p.dataset_id == "keyword_daily")
    dates = {
        json.loads(line)["date"]
        for line in daily.content.decode("utf-8").strip().split("\n")
        if line
    }
    assert dates == {"2026-01-05"}


@pytest.mark.asyncio
async def test_bid_decision_exported_in_current_state() -> None:
    """S22: bid probe AVAILABLE exports decision_cpm_curr on current_state row."""
    from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
        BidDecisionSourceStatus,
    )
    from tests.unit.ai_package_v1.keyword_performance.conftest import (
        GENERATED_AT,
        PERIOD,
        SHOP_ID,
        FakeKeywordDeps,
        build_fake_assembler,
        make_bid_decision_raw,
        make_daily_raw,
        make_scope_row,
    )

    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row()],
        overlap={111: [(SHOP_ID, 101)], 222: [(SHOP_ID, 101)]},
        daily_raw=[make_daily_raw()],
        bid_decision_status=BidDecisionSourceStatus.AVAILABLE,
        bid_decision_raw=[make_bid_decision_raw(cpm_curr=188.0)],
    )
    assembler = build_fake_assembler(deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=PERIOD,
        generated_at=GENERATED_AT,
    )
    current_payload = next(
        p for p in result.payloads if p.dataset_id == "keyword_current_state"
    )
    import json

    row = json.loads(current_payload.content.decode("utf-8").strip())
    assert row["decision_cpm_curr"] == 188.0
    assert row["observed_cpm"] != row["decision_cpm_curr"]


def test_bid_log_decision_class_documented() -> None:
    """S22: DATA_MAP labels bid_decision_log as DECISION-class source."""
    from app.modules.ai_package_v1.keyword_performance.domain.data_map_builder import (
        build_data_map,
    )

    cutoff = PackageCutoff.from_generated_at("2026-10-03T12:00:00Z")
    dm = build_data_map(
        cutoff=cutoff,
        daily_first=None,
        daily_last=None,
        position_first=None,
        position_last=None,
        export_period_note="test",
    )
    assert "bid_decision_log" in dm["per_source_cutoff"]
    assert "decision_time" in dm["per_source_cutoff"]["bid_decision_log"]
