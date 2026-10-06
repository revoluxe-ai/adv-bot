"""Сценарии S01–S26 аналитических окон AI Package.

Формулы проверяются на доменном сервисе. Транспорт только сверяет те же строки.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import cast
from unittest.mock import MagicMock

import pytest

from app.modules.ai_package_v1.analysis.campaign_reader import ChAnalysisCampaignReader
from app.modules.ai_package_v1.analysis.catalog import STANDARD_ROLLING_IDS, preset_window_ids
from app.modules.ai_package_v1.analysis.comparisons import judge_comparison
from app.modules.ai_package_v1.analysis.constants import (
    ANALYSIS_CONTRACT_LOGICAL,
    CAMPAIGNS_LOGICAL,
    CUTOFF_NOT_COMPLETENESS,
    KEYWORD_PRODUCT_SCOPE_LOGICAL,
    KEYWORD_WINDOWS_LOGICAL,
)
from app.modules.ai_package_v1.analysis.models import AnalysisBuildRequest, CampaignDailyFact
from app.modules.ai_package_v1.analysis.service import (
    AnalysisAggregationService,
    AnalysisBuildResult,
    project_transport_view,
)
from app.modules.ai_package_v1.analysis.validation import validate_analysis_files
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import (
    PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
    ExportManifest,
)
from app.modules.ai_package_v1.export.family_gaps import build_family_gap_catalog
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    KeywordLegRole,
    WindowSpendStatus,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import KeywordWindowRowV1
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.validator.package_validator import (
    PackageValidationError,
    validate_domain_manifest,
    validate_zip_package,
)
from app.modules.ai_package_v1.zip_transport.encode import decode_package, encode_package

pytestmark = pytest.mark.unit

GENERATED = "2026-10-06T12:00:00Z"
CUTOFF = date(2026, 10, 5)


def _scope(*extra: ExportScopeAdv) -> tuple[ExportScopeAdv, ...]:
    if extra:
        return extra
    return (
        ExportScopeAdv(
            shop_id="1",
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="pair",
            active_status="active",
            bot_active=False,
        ),
    )


def _fact(
    adv_id: int,
    stat_date: date,
    *,
    views: int | None = 10,
    clicks: int | None = 2,
    spend_rub: float | None = 5.0,
    added_to_cart: int | None = 1,
    orders: int | None = 4,
    order_sum_rub: float | None = 80.0,
) -> CampaignDailyFact:
    return CampaignDailyFact(
        adv_id=adv_id,
        stat_date=stat_date,
        views=views,
        clicks=clicks,
        spend_rub=spend_rub,
        added_to_cart=added_to_cart,
        orders=orders,
        order_sum_rub=order_sum_rub,
    )


def _days(start: date, end: date) -> list[date]:
    cursor = start
    found: list[date] = []
    while cursor <= end:
        found.append(cursor)
        cursor += timedelta(days=1)
    return found


def _build(
    *,
    generated_at: str = GENERATED,
    period: ExportPeriod | None = None,
    scope: tuple[ExportScopeAdv, ...] | None = None,
    facts: tuple[CampaignDailyFact, ...] = (),
    keyword_windows: tuple[KeywordWindowRowV1, ...] = (),
    keyword_history_first: date | None = None,
    keyword_history_last: date | None = None,
    campaign_source_complete_through: date | None = None,
    keyword_source_complete_through: date | None = None,
) -> AnalysisBuildResult:
    return AnalysisAggregationService().build(
        AnalysisBuildRequest(
            shop_id=1,
            generated_at=generated_at,
            period=period
            or ExportPeriod(start=date(2026, 10, 4), end=date(2026, 10, 5)),
            scope=scope if scope is not None else _scope(),
            campaign_facts=facts,
            keyword_windows=keyword_windows,
            keyword_history_first=keyword_history_first,
            keyword_history_last=keyword_history_last,
            campaign_source_complete_through=campaign_source_complete_through,
            keyword_source_complete_through=keyword_source_complete_through,
        )
    )


def _window(rows: list[dict[str, object]], window_id: str, adv_id: int | None) -> dict[str, object]:
    for row in rows:
        if row["window_id"] == window_id and row.get("adv_id") == adv_id:
            return row
    raise AssertionError(f"missing {window_id} adv={adv_id}")


def _metrics_of(row: dict[str, object]) -> dict[str, object]:
    metrics = row["metrics"]
    assert isinstance(metrics, dict)
    return cast(dict[str, object], metrics)


def _metric(row: dict[str, object], metric_id: str) -> object:
    cell = _metrics_of(row)[metric_id]
    assert isinstance(cell, dict)
    return cast(dict[str, object], cell)["value"]


def _codes(row: dict[str, object]) -> list[object]:
    reasons = row["reason_codes"]
    assert isinstance(reasons, list)
    return list(cast(list[object], reasons))


def _uncomputable(row: dict[str, object], metric_id: str) -> list[str]:
    items = row["uncomputable"]
    assert isinstance(items, list)
    typed_items = cast(list[object], items)
    for item in typed_items:
        assert isinstance(item, dict)
        entry = cast(dict[str, object], item)
        if entry.get("metric_id") == metric_id:
            reasons = entry.get("reason_codes")
            assert isinstance(reasons, list)
            return [str(reason) for reason in cast(list[object], reasons)]
    raise AssertionError(metric_id)


def _keyword_row() -> KeywordWindowRowV1:
    return KeywordWindowRowV1(
        shop_id=1,
        adv_id=111,
        leg_role=KeywordLegRole.AUTO,
        nmid=500,
        norm_query="boots",
        window_id="365d",
        window_start="2025-10-06",
        window_end="2026-10-05",
        observed_days=10,
        requested_days=365,
        partial=True,
        views_sum=10,
        clicks_sum=2,
        orders_sum=1,
        spend_rub_sum=5.0,
        spend_status=WindowSpendStatus.FACTUAL,
    )


def test_s01_window_is_not_keyword_history() -> None:
    """S01: история ключей длиннее 7 дней и не обрезается запрошенным периодом."""
    result = _build(
        period=ExportPeriod(start=date(2026, 10, 1), end=date(2026, 10, 5)),
        keyword_history_first=date(2025, 1, 1),
        keyword_history_last=date(2026, 10, 5),
        keyword_windows=(_keyword_row(),),
    )
    history = cast(dict[str, object], result.contract["history_context"])
    keyword = cast(dict[str, object], history["keyword_performance"])
    assert keyword["first"] == "2025-01-01"
    assert keyword["clipped_by_requested_period"] is False
    seven = _window(result.campaign_rows, "7d", 111)
    assert seven["window_start"] != "2025-01-01"
    assert result.keyword_rows[0]["window_id"] == "365d"
    assert result.keyword_rows[0]["window_start"] == "2025-10-06"
    names = {payload.logical_name for payload in result.payloads}
    assert KEYWORD_WINDOWS_LOGICAL not in names


def test_s02_one_day_excludes_generation_date() -> None:
    """S02: окно 1 дня кончается накануне сборки и само не становится полным."""
    result = _build(facts=(_fact(111, CUTOFF), _fact(222, CUTOFF)))
    one = _window(result.campaign_rows, "1d", 111)
    assert one["window_start"] == "2026-10-05"
    assert one["window_end"] == "2026-10-05"
    assert one["generation_utc_date"] == "2026-10-06"
    assert one["package_cutoff_date"] == "2026-10-05"
    assert one["coverage_status"] != "COMPLETE"
    assert "latest_complete_date" not in one
    assert "14d" in STANDARD_ROLLING_IDS
    assert _window(result.campaign_rows, "14d", 111)["window_end"] == "2026-10-05"


def test_s03_calendar_year_is_not_365d() -> None:
    """S03: предыдущий календарный год не совпадает с окном 365 дней."""
    result = _build(generated_at="2026-03-16T00:00:00Z")
    rolling = _window(result.campaign_rows, "365d", 111)
    calendar_year = _window(result.campaign_rows, "previous_year", 111)
    assert (rolling["window_start"], rolling["window_end"]) != (
        calendar_year["window_start"],
        calendar_year["window_end"],
    )
    assert calendar_year["window_start"] == "2025-01-01"
    assert calendar_year["window_end"] == "2025-12-31"
    assert rolling["window_end"] == "2026-03-15"


def test_s04_custom_period_is_not_a_preset() -> None:
    """S04: произвольный период не пресет и частичен, если включает дату сборки."""
    result = _build(
        period=ExportPeriod(start=date(2026, 10, 1), end=date(2026, 10, 6)),
        facts=(_fact(111, CUTOFF), _fact(222, CUTOFF)),
        campaign_source_complete_through=date(2026, 10, 6),
    )
    custom = _window(result.campaign_rows, "requested_custom", 111)
    presets = preset_window_ids(PackageCutoff.from_generated_at(GENERATED))
    assert custom["window_id"] not in presets
    assert custom["coverage_status"] == "PARTIAL"


def test_s05_raw_fact_is_not_copied_per_window() -> None:
    """S05: одна сырая строка даёт разные агрегаты 7 и 30 дней."""
    result = _build(facts=(_fact(111, CUTOFF), _fact(222, CUTOFF)))
    assert result.campaign_fact_count == 2
    seven = _window(result.campaign_rows, "7d", 111)
    thirty = _window(result.campaign_rows, "30d", 111)
    assert seven["observed_days"] == 1
    assert thirty["observed_days"] == 1
    assert seven is not thirty
    assert not any("daily" in payload.logical_name for payload in result.payloads)
    leg_rows = [row for row in result.campaign_rows if row["adv_id"] == 111]
    assert len(leg_rows) > 2
    assert all("stat_date" not in row for row in leg_rows)


def test_s06_gap_and_null_are_not_zero() -> None:
    """S06: разрыв DRR магазина и пустая метрика не становятся нулём."""
    result = _build(
        facts=(
            _fact(111, CUTOFF, views=None, orders=0, spend_rub=0.0),
            _fact(222, CUTOFF, views=1, orders=0, spend_rub=0.0),
        )
    )
    leg = _window(result.campaign_rows, "1d", 111)
    assert "CAMPAIGN_WB_STAT_VIEWS" not in _metrics_of(leg)
    assert _metric(leg, "CAMPAIGN_WB_STAT_ORDERS") == 0
    assert _metric(leg, "CAMPAIGN_WB_STAT_SPEND_RUB") == 0.0
    package = _window(result.package_rows, "1d", None)
    assert "SHOP_DRR" not in _metrics_of(package)
    reasons = _uncomputable(package, "SHOP_DRR")
    assert "BLOCKED_BY_COMMON_SALES" in reasons
    assert 0 not in reasons


def test_s07_auto_and_search_stay_separate() -> None:
    """S07: Auto и Search — разные строки, расход не сложен под одним id."""
    result = _build(
        facts=(_fact(111, CUTOFF, spend_rub=5.0), _fact(222, CUTOFF, spend_rub=7.0))
    )
    auto = _window(result.campaign_rows, "1d", 111)
    search = _window(result.campaign_rows, "1d", 222)
    assert auto["leg_role"] == "AUTO"
    assert search["leg_role"] == "SEARCH"
    assert _metric(auto, "CAMPAIGN_WB_STAT_SPEND_RUB") == 5.0
    assert _metric(search, "CAMPAIGN_WB_STAT_SPEND_RUB") == 7.0
    assert auto["included_adv_ids"] == [111]
    assert search["included_adv_ids"] == [222]


def test_s08_campaign_orders_are_not_direct() -> None:
    """S08: заказы статистики кампании не называются прямой атрибуцией."""
    result = _build(facts=(_fact(111, CUTOFF, orders=3), _fact(222, CUTOFF, orders=3)))
    leg = _window(result.campaign_rows, "1d", 111)
    assert leg["scope"] == "CAMPAIGN_WB_STAT"
    assert _metric(leg, "CAMPAIGN_WB_STAT_ORDERS") == 3
    assert "CPO_FACT_DIRECT" not in _metrics_of(leg)
    assert "CPO_FACT_LINKED" not in _metrics_of(leg)
    assert "BLOCKED_BY_ATTRIBUTION_FACTS" in _uncomputable(leg, "CPO_FACT_DIRECT")


def test_s09_linked_does_not_fall_back_to_direct() -> None:
    """S09: связанная метрика не получает прямое или кампанийное число."""
    result = _build(facts=(_fact(111, CUTOFF, orders=3), _fact(222, CUTOFF, orders=3)))
    leg = _window(result.campaign_rows, "1d", 111)
    linked = _uncomputable(leg, "CPO_FACT_LINKED")
    assert linked == ["BLOCKED_BY_ATTRIBUTION_FACTS"]
    assert "CPO_FACT_LINKED" not in _metrics_of(leg)
    assert "DRR_FACT_LINKED" not in _metrics_of(leg)
    assert _metrics_of(leg).get("CPO_FACT_DIRECT") is None


def test_s10_shop_drr_withheld() -> None:
    """S10: DRR магазина не считается из расхода пакета и суммы заказов рекламы."""
    result = _build(facts=(_fact(111, CUTOFF), _fact(222, CUTOFF)))
    package = _window(result.package_rows, "7d", None)
    assert "SHOP_DRR" not in _metrics_of(package)
    reasons = _uncomputable(package, "SHOP_DRR")
    assert reasons == [
        "BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE",
        "BLOCKED_BY_COMMON_SALES",
        "BLOCKED_BY_SHOP_DRR_SOURCE",
    ]
    assert "ALL_SHOP_AD_SPEND" not in _metrics_of(package)
    assert "CAMPAIGN_WB_STAT_ORDER_SUM" in _metrics_of(package)


def test_s11_fixed_cpo_is_not_rewritten() -> None:
    """S11: тождество целевого CPO не включает режим управления и не пишет в WB."""
    result = _build()
    assert result.contract["fixed_cpo_control_mode"] == "unchanged"
    assert result.contract["dynamic_cpo_control_enabled"] is False
    definitions = result.contract["metric_definitions"]
    assert isinstance(definitions, list)
    identity: dict[str, object] | None = None
    for item in cast(list[object], definitions):
        assert isinstance(item, dict)
        entry = cast(dict[str, object], item)
        if entry.get("metric_id") == "TARGET_CPO_IDENTITY":
            identity = entry
    assert identity is not None
    assert identity["computable"] is False
    assert identity["control_mode"] is False
    assert not any(payload.dataset_id == "wb_write" for payload in result.payloads)


def test_s12_zero_denominator_is_not_comparable() -> None:
    """S12: наблюдаемый ноль заказов делает сравнение несопоставимым."""
    end = CUTOFF
    start = end - timedelta(days=2)
    facts = tuple(
        _fact(adv_id, day, orders=0, spend_rub=5.0)
        for adv_id in (111, 222)
        for day in _days(start, end)
    )
    result = _build(facts=facts, campaign_source_complete_through=end)
    pair = next(
        row
        for row in result.comparison_rows
        if row["entity_kind"] == "CAMPAIGN_LEG"
        and row["adv_id"] == 111
        and row["left_window_id"] == "1d"
        and row["right_window_id"] == "3d"
    )
    assert pair["status"] == "NOT_COMPARABLE"
    assert "ZERO_DENOMINATOR" in _codes(pair)
    assert pair["nested"] is True
    assert pair["independent_sample"] is False


def test_s13_partial_coverage_stays_partial() -> None:
    """S13: неполное длинное окно даёт частичное сравнение, не два голых числа."""
    end = CUTOFF
    seven_start = end - timedelta(days=6)
    partial_start = end - timedelta(days=14)
    facts = tuple(
        _fact(111, day, orders=2)
        for day in _days(partial_start, end)
    )
    scope = (
        ExportScopeAdv(
            shop_id="1",
            auto_adv_id=111,
            search_adv_id=None,
            main_nmid=500,
            name="auto-only",
            active_status="active",
            bot_active=False,
        ),
    )
    result = _build(
        scope=scope,
        facts=facts,
        campaign_source_complete_through=end,
    )
    assert _window(result.campaign_rows, "7d", 111)["coverage_status"] == "COMPLETE"
    assert _window(result.campaign_rows, "30d", 111)["coverage_status"] == "PARTIAL"
    assert seven_start == date(2026, 9, 29)
    pair = next(
        row
        for row in result.comparison_rows
        if row["adv_id"] == 111
        and row["left_window_id"] == "7d"
        and row["right_window_id"] == "30d"
    )
    assert pair["status"] == "PARTIAL"
    assert _codes(pair) == ["PARTIAL_COVERAGE"]
    assert "status" in pair
    small = _build(
        scope=scope,
        facts=tuple(_fact(111, day, orders=1) for day in _days(seven_start, end)),
        campaign_source_complete_through=end,
    )
    one = _window(small.campaign_rows, "1d", 111)
    three = _window(small.campaign_rows, "3d", 111)
    one["metrics"] = {
        "CAMPAIGN_WB_STAT_ORDERS": {
            "value": 2,
            "metric_definition_version": "1.0.0",
        }
    }
    three["metrics"] = {
        "CAMPAIGN_WB_STAT_ORDERS": {
            "value": 2,
            "metric_definition_version": "1.0.0",
        }
    }
    judged = judge_comparison(
        left=one,
        right=three,
        left_window_id="1d",
        right_window_id="3d",
        relationship="NESTED",
        pair_index=0,
        entity_key=("CAMPAIGN_LEG", "CAMPAIGN_WB_STAT", "111", ""),
        orders_metric="CAMPAIGN_WB_STAT_ORDERS",
        cpo_metric="CAMPAIGN_WB_STAT_CPO",
    )
    assert judged["status"] == "PARTIAL"
    assert _codes(judged) == ["INSUFFICIENT_SAMPLE"]
    mismatched = dict(three)
    mismatched["metric_definition_version"] = "2.0.0"
    mismatched["metrics"] = {
        "CAMPAIGN_WB_STAT_ORDERS": {
            "value": 9,
            "metric_definition_version": "2.0.0",
        }
    }
    version_pair = judge_comparison(
        left=one,
        right=mismatched,
        left_window_id="1d",
        right_window_id="3d",
        relationship="NESTED",
        pair_index=0,
        entity_key=("CAMPAIGN_LEG", "CAMPAIGN_WB_STAT", "111", ""),
        orders_metric="CAMPAIGN_WB_STAT_ORDERS",
        cpo_metric="CAMPAIGN_WB_STAT_CPO",
    )
    assert version_pair["status"] == "NOT_COMPARABLE"
    assert _codes(version_pair) == ["INCOMPATIBLE_METRIC_VERSION"]
    absent = judge_comparison(
        left=one,
        right=None,
        left_window_id="1d",
        right_window_id="3d",
        relationship="NESTED",
        pair_index=0,
        entity_key=("CAMPAIGN_LEG", "CAMPAIGN_WB_STAT", "111", ""),
        orders_metric="CAMPAIGN_WB_STAT_ORDERS",
        cpo_metric="CAMPAIGN_WB_STAT_CPO",
    )
    assert _codes(absent) == ["ENTITY_ABSENT"]


def test_s14_guide_forbids_gap_as_zero() -> None:
    """S14: инструкция запрещает ноль вместо разрыва и подмену DRR магазина."""
    guide = _build().guide_text
    assert CUTOFF_NOT_COMPLETENESS in guide
    assert "Do not treat GAP, unknown, or a missing row as zero." in guide
    assert "Do not merge Auto and Search." in guide
    assert "Do not treat package campaign scope as whole-shop spend." in guide
    assert "Do not calculate SHOP_DRR from package scope." in guide
    assert "Do not treat keyword-product scope as total SKU economics." in guide
    assert "Do not silently fall LINKED back to DIRECT." in guide
    assert "Do not invent attribution." in guide
    assert "Do not invent causality." in guide
    assert "Do not assume a nominal window is complete without evidence." in guide


def test_s15_repeat_build_keeps_order() -> None:
    """S15: повторный расчёт на тех же фактах сохраняет порядок строк."""
    facts = (
        _fact(222, CUTOFF, orders=2),
        _fact(111, CUTOFF - timedelta(days=1), orders=2),
        _fact(111, CUTOFF, orders=2),
    )
    first = _build(facts=facts)
    second = _build(facts=facts)
    assert [row["window_id"] for row in first.campaign_rows] == [
        row["window_id"] for row in second.campaign_rows
    ]
    assert first.payloads[3].content == second.payloads[3].content
    assert first.comparison_rows == second.comparison_rows


def test_s16_transports_share_domain_rows() -> None:
    """S16: ZIP и API читают один доменный результат и не вводят вторую формулу."""
    result = _build(facts=(_fact(111, CUTOFF), _fact(222, CUTOFF)))
    zip_view = project_transport_view(result, "zip")
    api_view = project_transport_view(result, "mcp")
    assert zip_view["campaign_rows"] == api_view["campaign_rows"]
    assert zip_view["comparison_rows"] == api_view["comparison_rows"]
    assert zip_view["campaign_rows"] is result.campaign_rows


def test_s17_manifest_lists_analysis_contract() -> None:
    """S17: манифест ссылается на контракт анализа и его хеш."""
    result = _build(facts=(_fact(111, CUTOFF), _fact(222, CUTOFF)))
    manifest = ExportManifest(
        package_schema_version=PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
        shop_id=1,
        period=ExportPeriod(start=date(2026, 10, 4), end=CUTOFF),
        generated_at=GENERATED,
        datasets=result.cards,
    )
    zip_bytes = encode_package(manifest, result.payloads)
    validate_zip_package(zip_bytes)
    decoded, files = decode_package(zip_bytes)
    listed = {entry["logical_name"] for entry in decoded["files"]}
    assert ANALYSIS_CONTRACT_LOGICAL in listed
    assert ANALYSIS_CONTRACT_LOGICAL in files


def test_s18_caller_period_does_not_clip_30d(monkeypatch: pytest.MonkeyPatch) -> None:
    """S18: узкий период вызывающей стороны не режет чтение и окно 30 дней."""
    early = CUTOFF - timedelta(days=40)
    facts = tuple(_fact(111, day, orders=1) for day in _days(early, CUTOFF))
    facts += tuple(_fact(222, day, orders=1) for day in _days(early, CUTOFF))
    result = _build(
        period=ExportPeriod(start=CUTOFF, end=CUTOFF),
        facts=facts,
        campaign_source_complete_through=CUTOFF,
    )
    thirty = _window(result.campaign_rows, "30d", 111)
    assert int(str(thirty["observed_days"])) == 30
    assert result.contract["requested_period"] == {
        "start": "2026-10-05",
        "end": "2026-10-05",
    }
    query = ChAnalysisCampaignReader().query_text
    assert "default_db.full_adv_wb_stat" in query
    assert "argMax(spend, version)" in query
    assert "start_date" not in query
    assert "full_adv_wb_stat_hourly" not in query
    captured: dict[str, object] = {}

    class _Client:
        async def query(self, sql: str, parameters: dict[str, object]) -> MagicMock:
            captured["sql"] = sql
            captured["parameters"] = parameters
            return MagicMock(result_rows=[])

    import asyncio

    asyncio.run(
        ChAnalysisCampaignReader().fetch_daily_facts_with_client(
            _Client(),
            shop_id=1,
            adv_ids=[111],
            end_date=date(2026, 10, 6),
        )
    )
    parameters = captured["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["end_date"] == "2026-10-06"
    assert "start_date" not in parameters
    _ = monkeypatch


def test_s19_analysis_package_is_not_schema_1_0_0() -> None:
    """S19: пакет с анализом поднимает схему до 1.1.0."""
    result = _build()
    assert result.package_schema_version == "1.1.0"
    assert result.contract["analysis_contract_version"] == "1.0.0"
    assert result.contract["package_schema_version"] == "1.1.0"


def test_s20_encoder_does_not_duplicate_keyword_windows() -> None:
    """S20: кодировщик не создаёт вторую копию ключевых окон."""
    result = _build(keyword_windows=(_keyword_row(),))
    names = [payload.logical_name for payload in result.payloads]
    assert names.count(KEYWORD_WINDOWS_LOGICAL) == 0
    assert "analysis/windows/keywords.jsonl" not in names
    assert "analysis/windows/shop.jsonl" not in names
    assert "analysis/windows/products.jsonl" not in names
    assert KEYWORD_PRODUCT_SCOPE_LOGICAL in names
    assert CAMPAIGNS_LOGICAL in names
    from pathlib import Path

    assembler = Path(
        "app/modules/ai_package_v1/export/package_zip_assembler.py"
    ).read_text(encoding="utf-8")
    assert "AnalysisAggregationService" not in assembler
    assert "keyword_windows.jsonl" not in assembler


def test_s21_windows_do_not_close_store_drr_gap() -> None:
    """S21: окна не закрывают разрыв DRR магазина, настроек, событий и продаж."""
    catalog = build_family_gap_catalog()
    by_id = {entry["family_id"]: entry for entry in catalog}
    for family_id in (
        "store_drr",
        "campaign_settings_history",
        "campaign_change_events",
        "shop_product_orders_sales_feed",
    ):
        assert by_id[family_id]["status"] == "GAP"
    result = _build(facts=(_fact(111, CUTOFF), _fact(222, CUTOFF)))
    assert "SHOP_DRR" not in _metrics_of(_window(result.package_rows, "30d", None))


def test_s22_tampered_contract_fails_validation() -> None:
    """S22: порча байтов контракта ломает проверку пакета."""
    result = _build()
    manifest = ExportManifest(
        package_schema_version=PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
        shop_id=1,
        period=ExportPeriod(start=date(2026, 10, 4), end=CUTOFF),
        generated_at=GENERATED,
        datasets=result.cards,
    )
    zip_bytes = encode_package(manifest, result.payloads)
    decoded, files = decode_package(zip_bytes)
    files[ANALYSIS_CONTRACT_LOGICAL] = b'{"tampered":true}\n'
    with pytest.raises(PackageValidationError, match="hash mismatch"):
        validate_domain_manifest(decoded, files)


def test_s23_uncomputable_economics_are_not_zero() -> None:
    """S23: экономические метрики без источника не число и не ноль."""
    result = _build(facts=(_fact(111, CUTOFF, orders=4), _fact(222, CUTOFF, orders=4)))
    leg = _window(result.campaign_rows, "1d", 111)
    package = _window(result.package_rows, "1d", None)
    for metric_id in (
        "CPO_FACT_DIRECT",
        "DRR_FACT_DIRECT",
        "CPO_FACT_LINKED",
        "DRR_FACT_LINKED",
    ):
        assert metric_id not in _metrics_of(leg)
        assert _uncomputable(leg, metric_id) == ["BLOCKED_BY_ATTRIBUTION_FACTS"]
    assert "SHOP_DRR" not in _metrics_of(package)
    assert "ALL_SHOP_AD_SPEND" not in _metrics_of(package)
    encoded = json.dumps(_metrics_of(package))
    assert "SHOP_DRR" not in encoded


def test_s24_cutoff_does_not_prove_campaign_day() -> None:
    """S24: граница 2026-10-05 не делает 1d полным, если источник полон по 2026-09-25."""
    result = _build(
        facts=(_fact(111, date(2026, 9, 25)), _fact(222, date(2026, 9, 25))),
        campaign_source_complete_through=date(2026, 9, 25),
    )
    one = _window(result.campaign_rows, "1d", 111)
    assert one["window_start"] == "2026-10-05"
    assert one["window_end"] == "2026-10-05"
    assert one["coverage_status"] == "NO_DATA"
    assert one["source_complete_through"] == "2026-09-25"
    assert one["coverage_status"] != "COMPLETE"
    assert "latest_complete_date" not in result.contract


def test_s25_package_scope_is_not_whole_shop_spend() -> None:
    """S25: сумма ног пакета не называется расходом всего магазина."""
    result = _build(
        facts=(_fact(111, CUTOFF, spend_rub=5.0), _fact(222, CUTOFF, spend_rub=9.0)),
        campaign_source_complete_through=CUTOFF,
    )
    package = _window(result.package_rows, "1d", None)
    assert package["scope"] == "PACKAGE_CAMPAIGN_SCOPE"
    assert package["entity_kind"] == "PACKAGE_CAMPAIGN_SCOPE"
    assert _metric(package, "CAMPAIGN_WB_STAT_SPEND_RUB") == 14.0
    assert "ALL_SHOP_AD_SPEND" not in _metrics_of(package)
    assert "SHOP_AD_SPEND" not in _metrics_of(package)
    assert "BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE" in _uncomputable(
        package, "ALL_SHOP_AD_SPEND"
    )
    assert "SHOP_DRR" not in _metrics_of(package)


def test_s26_keyword_product_is_not_sku_economics() -> None:
    """S26: артикул ключевой истории не изображает всю экономику товара."""
    result = _build(keyword_windows=(_keyword_row(),))
    row = result.keyword_rows[0]
    assert row["scope"] == "KEYWORD_PERFORMANCE_PRODUCT_SCOPE"
    assert row["nmid"] == 500
    assert "SKU_GMV" not in _metrics_of(row)
    assert "SKU_DRR" not in _metrics_of(row)
    assert "SKU_ORDERS" not in _metrics_of(row)
    assert "KEYWORD_SCOPE_IS_NOT_TOTAL_SKU_ECONOMICS" in _uncomputable(row, "SKU_GMV")
    assert "CPO_FACT_DIRECT" not in _metrics_of(row)
    names = {payload.logical_name for payload in result.payloads}
    assert KEYWORD_PRODUCT_SCOPE_LOGICAL in names
    assert "analysis/windows/products.jsonl" not in names


def test_analysis_files_reject_false_complete() -> None:
    """Валидатор отвергает COMPLETE без доказательства источника."""
    result = _build()
    files = {payload.logical_name: payload.content for payload in result.payloads}
    validate_analysis_files(files, schema_version="1.1.0")
    forged = dict(files)
    forged[CAMPAIGNS_LOGICAL] = (
        b'{"coverage_status":"COMPLETE","source_complete_through":null,'
        b'"window_id":"7d","metrics":{},"nominal_window_end":"2026-10-05"}\n'
    )
    with pytest.raises(Exception, match="COMPLETE coverage"):
        validate_analysis_files(forged, schema_version="1.1.0")
