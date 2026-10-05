"""Contract tests: no WB, no writes, cutoff, manifest, cross-shop (S26,S28,S30,S37,S38,S51,...)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.ai_package_v1.domain.enums import DatasetId
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import DomainPayload
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.export.keyword_assembler import (
    KeywordAssemblyResult,
    KeywordPerformanceAssembler,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    BidDecisionSourceStatus,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader import (
    ChKeywordDailyReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    ChKeywordPositionReader,
)
from app.modules.ai_package_v1.keyword_performance.scope.adv_id_collector import (
    collect_keyword_export_scope,
)
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    FakeKeywordDeps,
    GENERATED_AT,
    SHOP_ID,
    build_fake_assembler,
    make_bid_decision_raw,
    make_daily_raw,
    make_position_raw,
    make_scope_row,
)

CUTOFF_GENERATED_AT = "2026-01-07T12:00:00Z"
CUTOFF_PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))

pytestmark = pytest.mark.unit

PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))


def _jsonl_dates(payload: DomainPayload) -> set[str]:
    content = payload.content.decode("utf-8").strip()
    if not content:
        return set()
    return {str(json.loads(line)["date"]) for line in content.split("\n") if line}


def _payload_by_id(result: KeywordAssemblyResult, dataset_id: str) -> DomainPayload:
    return next(p for p in result.payloads if p.dataset_id == dataset_id)


class _NoOpReader:
    async def fetch_rows(self, *args: object, **kwargs: object) -> list[object]:
        return []

    async def max_full_adv_version(self, *args: object, **kwargs: object) -> None:
        return None

    async def max_common_stat_version(self, *args: object, **kwargs: object) -> None:
        return None


def _scope() -> list[ExportScopeAdv]:
    return [
        ExportScopeAdv(
            shop_id=SHOP_ID,
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="auto",
            active_status="active",
            bot_active=False,
        )
    ]


def _empty_settings_snapshot() -> object:
    from datetime import UTC

    from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
        CampaignSettingsSnapshotV1,
        CompletenessBlockV1,
    )
    from app.modules.ai_package_v1.domain.settings_enums import (
        SettingsCollectionOutcome,
        SettingsCoverageLevel,
        SettingsFreshnessLevel,
    )

    return CampaignSettingsSnapshotV1(
        shop_id=SHOP_ID,
        snapshot_assembled_at=datetime.now(tz=UTC),
        records=(),
        completeness=CompletenessBlockV1(
            collection_outcome=SettingsCollectionOutcome.NO_DATA,
            coverage=SettingsCoverageLevel.UNKNOWN,
            freshness=SettingsFreshnessLevel.UNKNOWN,
        ),
    )


@pytest.mark.asyncio
async def test_keyword_export_no_wb(fake_deps: FakeKeywordDeps) -> None:
    """S37: keyword export path makes zero WB API calls."""
    wb_spy = MagicMock()
    assembler = build_fake_assembler(fake_deps)
    with patch.dict("sys.modules", {"app.core.mp.wb.api": wb_spy}):
        _ = await assembler.assemble(
            shop_id=SHOP_ID,
            manifest_shop_id="1",
            period=PERIOD,
            generated_at=GENERATED_AT,
        )
    wb_spy.assert_not_called()


@pytest.mark.asyncio
async def test_keyword_export_no_writes(fake_deps: FakeKeywordDeps) -> None:
    """S38: injected fake readers — no PG commit, Redis write, CH command."""
    assembler = build_fake_assembler(fake_deps)
    pg_commit = MagicMock()
    redis_set = MagicMock()
    ch_command = AsyncMock()
    with (
        patch(
            "app.utils.db.session_maker.get_async_session_maker",
            side_effect=AssertionError("PG session must not open"),
        ),
        patch("redis.asyncio.Redis.set", redis_set),
        patch(
            "app.utils.click_house.client.get_clickhouse_client",
            side_effect=AssertionError("CH client must not open"),
        ),
    ):
        _ = await assembler.assemble(
            shop_id=SHOP_ID,
            manifest_shop_id="1",
            period=PERIOD,
            generated_at=GENERATED_AT,
        )
    pg_commit.assert_not_called()
    redis_set.assert_not_called()
    ch_command.assert_not_called()


@pytest.mark.asyncio
async def test_contract_cutoff_future_dates() -> None:
    """S51: reader passes package_cutoff_date and instant to CH SQL filters."""
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
    assert client.query.await_count >= 1
    params = client.query.await_args_list[-1].kwargs.get("parameters") or client.query.await_args_list[-1][1].get("parameters")
    assert params["package_cutoff_date"] == "2026-10-05"
    assert params["package_cutoff_instant"] == "2026-10-05 15:00:00"
    sql = reader.query_text
    assert "timestamp <= {package_cutoff_instant:DateTime}" in sql
    assert "version <= {cutoff_instant_ms" not in sql


@pytest.mark.asyncio
async def test_contract_position_cutoff_instant_ms() -> None:
    """S51: position reader passes cutoff_instant_ms to CH SQL filters."""
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
    params = client.query.await_args_list[-1].kwargs.get("parameters") or client.query.await_args_list[-1][1].get("parameters")
    assert params["package_cutoff_date"] == "2026-10-05"
    assert params["cutoff_instant_ms"] == cutoff.cutoff_instant_ms
    sql = reader.query_text
    assert "version <= {cutoff_instant_ms" in sql


@pytest.mark.asyncio
async def test_multi_year_daily_fetch_merges_all_batches() -> None:
    """Multi-year partition loop returns rows from each year batch."""
    cutoff = PackageCutoff.from_generated_at("2026-10-05T15:00:00Z")
    client = AsyncMock()

    async def _query(*args: object, **kwargs: object) -> MagicMock:
        params_obj: object = kwargs.get("parameters")
        if params_obj is None and len(args) > 1:
            params_obj = args[1]
        start = ""
        if isinstance(params_obj, dict):
            params_dict = cast(dict[str, object], params_obj)
            start = str(params_dict.get("first_available", ""))
        if start.startswith("2025"):
            return MagicMock(
                result_rows=[
                    (
                        111,
                        500,
                        "q",
                        date(2025, 12, 31),
                        None,
                        1,
                        (100, 10, 5, 2, 50.0, 100.0, 5.0, 5.0, 0.1),
                    )
                ]
            )
        return MagicMock(
            result_rows=[
                (
                    111,
                    500,
                    "q",
                    date(2026, 1, 2),
                    None,
                    1,
                    (100, 10, 5, 2, 50.0, 100.0, 5.0, 5.0, 0.1),
                )
            ]
        )

    client.query = AsyncMock(side_effect=_query)
    reader = ChKeywordDailyReader()
    rows = await reader.fetch_rows_with_client(
        client,
        adv_ids=frozenset({111}),
        first_available=date(2025, 12, 1),
        cutoff=cutoff,
    )
    dates = {r.stat_date.isoformat() for r in rows}
    assert dates == {"2025-12-31", "2026-01-02"}
    assert client.query.await_count == 2


@pytest.mark.asyncio
async def test_cross_shop_forbidden() -> None:
    """S26: foreign-shop adv_id flagged; not trusted for bounds fetch."""
    row = make_scope_row(rebound_auto=frozenset({888}))
    overlap = {888: [("999", 202)]}
    scope = collect_keyword_export_scope([row], overlap)
    assert "FOREIGN_SHOP_ADV_ID" in scope.reason_codes
    trusted = frozenset(
        a.adv_id for a in scope.assignments if not a.foreign_shop and not a.ambiguous_ownership
    )
    assert 888 not in trusted


@pytest.mark.asyncio
async def test_export_no_store_writes(fake_deps: FakeKeywordDeps) -> None:
    """S28: read-only seam — assembler completes without persistence side effects."""
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=PERIOD,
        generated_at=GENERATED_AT,
    )
    assert result.payloads
    assert all(p.content is not None for p in result.payloads)


def test_no_second_exporter_entry() -> None:
    """S30: ExportService remains sole keyword export authority."""
    import inspect

    from app.modules.ai_package_v1.export import export_service

    source = inspect.getsource(export_service)
    assert "KeywordPerformanceAssembler" in source
    assert "keyword_assembler.assemble" in source.replace(" ", "")


@pytest.mark.asyncio
async def test_datamap_in_manifest_files(fake_deps: FakeKeywordDeps) -> None:
    """S31: DATA_MAP payload present in assembler output."""
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id="1", period=PERIOD, generated_at=GENERATED_AT
    )
    logical = {p.logical_name for p in result.payloads}
    assert "DATA_MAP.json" in logical


@pytest.mark.asyncio
async def test_injected_fake_reader(fake_deps: FakeKeywordDeps) -> None:
    """S33: fake reader returns controlled daily rows."""
    fake_deps.daily_raw.append(make_daily_raw(stat_date=date(2026, 2, 1), views=42))
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id="1", period=PERIOD, generated_at=GENERATED_AT
    )
    daily = next(p for p in result.payloads if p.dataset_id == "keyword_daily")
    assert b'"views": 42' in daily.content or b'"views":42' in daily.content


@pytest.mark.asyncio
async def test_keyword_cards_in_manifest(fake_deps: FakeKeywordDeps) -> None:
    """S29: keyword datasets appear in ExportService manifest."""
    service = ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=MagicMock(),
        keyword_assembler=build_fake_assembler(fake_deps),
    )
    service._settings_assembler.assemble = AsyncMock(  # type: ignore[method-assign, union-attr]
        return_value=_empty_settings_snapshot()
    )
    export = await service.export_with_scope(
        SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
    )
    ids = {c.dataset_id for c in export.manifest.datasets}
    assert DatasetId.KEYWORD_WINDOWS in ids
    assert DatasetId.KEYWORD_CHANGES in ids


@pytest.mark.asyncio
async def test_contract_full_history(fake_deps: FakeKeywordDeps) -> None:
    """S39: dates beyond ExportPeriod.end included when within cutoff."""
    fake_deps.daily_raw.append(make_daily_raw(stat_date=date(2026, 3, 1)))
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id="1", period=PERIOD, generated_at=GENERATED_AT
    )
    daily = next(p for p in result.payloads if p.dataset_id == "keyword_daily")
    lines = daily.content.decode("utf-8").strip().split("\n")
    dates = {json.loads(line)["date"] for line in lines if line}
    assert "2026-03-01" in dates


@pytest.mark.asyncio
async def test_contract_rebound_scope(fake_deps: FakeKeywordDeps) -> None:
    """S40: rebound adv_id included in scope expansion."""
    fake_deps.scope_rows = [make_scope_row(rebound_auto=frozenset({999}))]
    fake_deps.overlap[999] = [(SHOP_ID, 101)]
    fake_deps.daily_raw.append(make_daily_raw(adv_id=999))
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id="1", period=PERIOD, generated_at=GENERATED_AT
    )
    daily = next(p for p in result.payloads if p.dataset_id == "keyword_daily")
    assert b'"adv_id": 999' in daily.content or b'"adv_id":999' in daily.content


@pytest.mark.asyncio
async def test_contract_null_spend(fake_deps: FakeKeywordDeps) -> None:
    """S41: null spend exported as unavailable, not zero."""
    fake_deps.daily_raw = [make_daily_raw(spend=None)]
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id="1", period=PERIOD, generated_at=GENERATED_AT
    )
    daily = next(p for p in result.payloads if p.dataset_id == "keyword_daily")
    row = json.loads(daily.content.decode("utf-8").strip().split("\n")[0])
    assert row["spend_rub"] is None


@pytest.mark.asyncio
async def test_contract_null_position(fake_deps: FakeKeywordDeps) -> None:
    """S42: null position not coerced."""
    fake_deps.daily_raw = [make_daily_raw(avr_pos=None)]
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id="1", period=PERIOD, generated_at=GENERATED_AT
    )
    daily = next(p for p in result.payloads if p.dataset_id == "keyword_daily")
    row = json.loads(daily.content.decode("utf-8").strip().split("\n")[0])
    assert row["cluster_avg_pos"] is None


@pytest.mark.asyncio
async def test_bid_log_unsupported_coverage(fake_deps: FakeKeywordDeps) -> None:
    """S48: bid_decision_log unsupported when probe returns false."""
    fake_deps.bid_decision_status = BidDecisionSourceStatus.UNSUPPORTED
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id="1", period=PERIOD, generated_at=GENERATED_AT
    )
    coverage = next(p for p in result.payloads if p.dataset_id == "keyword_coverage")
    doc = json.loads(coverage.content.decode("utf-8"))
    assert doc["datasets"]["bid_decision_log"]["status"] == "UNSUPPORTED"
    assert "UNSUPPORTED" in doc["reason_codes"]


@pytest.mark.asyncio
async def test_contract_cutoff_excludes_future_date_payload() -> None:
    """S51: future fixture date absent from export payloads and bounds metadata."""
    from datetime import UTC

    from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
        BidDecisionSourceStatus,
    )
    from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
        SourceBounds,
    )

    valid_decision = make_bid_decision_raw(cpm_curr=150.0)
    future_decision = make_bid_decision_raw(
        cpm_curr=999.0,
        decision_time=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
        stats_max_timestamp=datetime(2026, 3, 1, 9, 0, 0, tzinfo=UTC),
    )
    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row()],
        overlap={111: [(SHOP_ID, 101)], 222: [(SHOP_ID, 101)]},
        daily_raw=[
            make_daily_raw(stat_date=date(2026, 1, 5), views=11),
            make_daily_raw(stat_date=date(2026, 3, 1), views=99),
        ],
        position_raw=[
            make_position_raw(stat_date=date(2026, 1, 5)),
            make_position_raw(stat_date=date(2026, 3, 1)),
        ],
        daily_bounds=SourceBounds(date(2026, 1, 1), date(2026, 3, 1)),
        position_bounds=SourceBounds(date(2026, 1, 1), date(2026, 3, 1)),
        bid_decision_status=BidDecisionSourceStatus.AVAILABLE,
        bid_decision_raw=[valid_decision, future_decision],
        bid_decision_timeline=[valid_decision, future_decision],
    )
    result = await build_fake_assembler(deps).assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=CUTOFF_PERIOD,
        generated_at=CUTOFF_GENERATED_AT,
    )
    daily_dates = _jsonl_dates(_payload_by_id(result, "keyword_daily"))
    position_dates = _jsonl_dates(_payload_by_id(result, "keyword_positions"))
    assert daily_dates == {"2026-01-05"}
    assert "2026-03-01" not in position_dates
    data_map = json.loads(_payload_by_id(result, "DATA_MAP").content.decode("utf-8"))
    bounds = data_map["keyword_history_bounds"]
    assert bounds["daily_last_available"] == "2026-01-05"
    assert bounds["position_last_available"] == "2026-01-05"
    coverage = json.loads(_payload_by_id(result, "keyword_coverage").content.decode("utf-8"))
    assert coverage["datasets"]["keyword_daily"]["last_available"] == "2026-01-05"
    decisions = _payload_by_id(result, "keyword_decisions").content.decode("utf-8")
    assert "999.0" not in decisions
    assert "150.0" in decisions


@pytest.mark.asyncio
async def test_contract_cutoff_excludes_same_day_post_instant_daily_payload() -> None:
    """S51: same-day daily row with timestamp > generated_at excluded from payloads."""
    from datetime import UTC

    from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
        SourceBounds,
    )

    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row()],
        overlap={111: [(SHOP_ID, 101)], 222: [(SHOP_ID, 101)]},
        daily_raw=[
            make_daily_raw(
                stat_date=date(2026, 1, 5),
                last_snapshot_ts=datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
                views=11,
            ),
            make_daily_raw(
                stat_date=date(2026, 1, 7),
                last_snapshot_ts=datetime(2026, 1, 7, 15, 0, 0, tzinfo=UTC),
                views=99,
            ),
        ],
        daily_bounds=SourceBounds(date(2026, 1, 1), date(2026, 1, 7)),
    )
    result = await build_fake_assembler(deps).assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=CUTOFF_PERIOD,
        generated_at=CUTOFF_GENERATED_AT,
    )
    daily_dates = _jsonl_dates(_payload_by_id(result, "keyword_daily"))
    assert daily_dates == {"2026-01-05"}
    windows = _payload_by_id(result, "keyword_windows").content.decode("utf-8")
    assert "2026-01-07" not in windows or '"date": "2026-01-07"' not in windows


@pytest.mark.asyncio
async def test_contract_cutoff_excludes_future_position_version_payload() -> None:
    """S51: position row with version ms > cutoff_instant_ms excluded from payloads."""
    from datetime import UTC

    from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
        SourceBounds,
    )

    cutoff = PackageCutoff.from_generated_at(CUTOFF_GENERATED_AT)
    valid_version = cutoff.cutoff_instant_ms - 3_600_000
    future_version = int(datetime(2026, 1, 7, 15, 0, 0, tzinfo=UTC).timestamp() * 1000)
    assert future_version > cutoff.cutoff_instant_ms

    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row()],
        overlap={111: [(SHOP_ID, 101)], 222: [(SHOP_ID, 101)]},
        daily_raw=[make_daily_raw(stat_date=date(2026, 1, 5))],
        position_raw=[
            make_position_raw(stat_date=date(2026, 1, 5), version=valid_version),
            make_position_raw(stat_date=date(2026, 1, 7), version=future_version),
        ],
        position_bounds=SourceBounds(date(2026, 1, 1), date(2026, 1, 7)),
    )
    result = await build_fake_assembler(deps).assemble(
        shop_id=SHOP_ID,
        manifest_shop_id="1",
        period=CUTOFF_PERIOD,
        generated_at=CUTOFF_GENERATED_AT,
    )
    position_dates = _jsonl_dates(_payload_by_id(result, "keyword_positions"))
    assert position_dates == {"2026-01-05"}
    current = json.loads(
        _payload_by_id(result, "keyword_position_current").content.decode("utf-8").strip()
    )
    assert current["observation_date"] == "2026-01-05"


@pytest.mark.asyncio
async def test_default_export_service_keyword_enabled() -> None:
    """S49/S50: default ExportService constructor wires keyword assembler."""
    from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
        BidDecisionAvailability,
        BidDecisionSourceStatus,
    )

    from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
        SourceBounds,
    )

    probe = AsyncMock()
    probe.probe = AsyncMock(
        return_value=BidDecisionAvailability(
            status=BidDecisionSourceStatus.UNSUPPORTED
        )
    )
    scope_reader = AsyncMock()
    scope_reader.load_keyword_scope = AsyncMock(return_value=([], False))
    scope_reader.load_global_adv_id_overlap = AsyncMock(return_value={})
    bounds_reader = AsyncMock()
    bounds_reader.fetch_daily_bounds = AsyncMock(
        return_value=SourceBounds(None, None)
    )
    bounds_reader.fetch_position_bounds = AsyncMock(
        return_value=SourceBounds(None, None)
    )
    daily_reader = AsyncMock()
    daily_reader.fetch_rows = AsyncMock(return_value=[])
    position_reader = AsyncMock()
    position_reader.fetch_rows = AsyncMock(return_value=[])
    policy_reader = AsyncMock()
    policy_reader.load_policies = AsyncMock(return_value={})
    settings = MagicMock()
    settings.assemble = AsyncMock(return_value=_empty_settings_snapshot())
    service = ExportService(
        scope_reader=scope_reader,
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=settings,
        keyword_assembler=KeywordPerformanceAssembler(
            scope_reader=scope_reader,
            bounds_reader=bounds_reader,
            daily_reader=daily_reader,
            position_reader=position_reader,
            bid_decision_probe=probe,
            policy_reader=policy_reader,
        ),
    )
    result = await service.export_with_scope(
        SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
    )
    assert any(c.dataset_id == DatasetId.KEYWORD_DAILY for c in result.manifest.datasets)
