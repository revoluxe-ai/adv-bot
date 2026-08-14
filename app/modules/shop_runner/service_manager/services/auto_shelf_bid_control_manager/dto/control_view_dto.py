"""DTO СЌРєСЂР°РЅР° Telegram РґР»СЏ Auto Shelf Bid Control."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from .optimization_metric import OptimizationMetric
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)


@dataclass(frozen=True, slots=True)
class BidPointStatsDTO:
    """РЎС‚Р°С‚РёСЃС‚РёРєР° РїРѕ РѕРґРЅРѕР№ С‚РѕС‡РєРµ СЃС‚Р°РІРєРё РґР»СЏ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ РІ Telegram.

    ``cart_cpa`` вЂ” CPC score (РЅРµ CPA РєРѕСЂР·РёРЅС‹), СЃРј. ``BidStatsDTO.cart_cpa``.
    """

    bid_minor: int  # РєРѕРїРµР№РєРё (РєР°Рє РІ CH auto_shelf_bid_intervals)
    currency: str
    last_interval_at: datetime | None  # РїРѕСЃР»РµРґРЅРёР№ РёРЅС‚РµСЂРІР°Р» РїРѕ СЃС‚Р°РІРєРµ (РґР»СЏ СЃРѕСЂС‚РёСЂРѕРІРєРё UI)
    impressions: int
    clicks: int
    carts: int
    orders: int
    spend: float
    cart_cpa: float | None
    ctr: float | None
    cart_cr: float | None
    is_covered: bool
    is_best: bool
    is_current_main: bool
    is_current_test: bool


@dataclass(frozen=True, slots=True)
class CoverageLayerBidDTO:
    """Строка диагностики accumulated coverage layers для одной ставки."""

    label: str
    bid_minor: int
    impressions: int
    valid_hours: int
    closed_layers: int
    undercovered: bool
    is_current_main: bool = False
    is_current_test: bool = False
    is_selected_next_test: bool = False
    is_best_plan: bool = False
    is_global_best: bool = False
    status_text: str | None = None
    expected_daily_impressions: float | None = None
    expected_daily_clicks: float | None = None
    expected_daily_orders: float | None = None
    expected_order_cost_rub: float | None = None
    ctr: float | None = None
    plan_distance_score: float | None = None


@dataclass(frozen=True, slots=True)
class AutoShelfBidControlViewDTO:

    # TODO: Найти и исправить битую кодировку
    """РЎСЂРµР· СЃРѕСЃС‚РѕСЏРЅРёСЏ control-РјРѕРґСѓР»СЏ РґР»СЏ Telegram-СЌРєСЂР°РЅР°."""

    nmid: int
    auto_adv_id: int | None
    enabled: bool
    has_settings: bool
    has_state: bool
    dry_run: bool  # РіР»РѕР±Р°Р»СЊРЅРѕ: settings.AUTO_SHELF_BID_CONTROL_DRY_RUN
    bid_units_confirmed: bool
    actual_bid_minor: int | None  # РєРѕРїРµР№РєРё, Redis recommendations
    min_bid_minor: int | None  # РєРѕРїРµР№РєРё, РјРёРЅ. СЃС‚Р°РІРєР° WB (РёР· min_bids cache)
    max_bid_minor: int | None  # РєРѕРїРµР№РєРё, РЅР°СЃС‚СЂРѕР№РєР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    current_main_bid_minor: int | None  # РєРѕРїРµР№РєРё
    current_test_bid_minor: int | None  # РєРѕРїРµР№РєРё
    cycle_best_bid_minor: int | None  # РєРѕРїРµР№РєРё, Р»СѓС‡С€РёР№ CPC РІ С‚РµРєСѓС‰РµРј С†РёРєР»Рµ
    global_best_bid_minor: int | None  # РєРѕРїРµР№РєРё, min CPC С‚РµРєСѓС‰РёР№ в€Є РїСЂРµРґС‹РґСѓС‰РёР№ С†РёРєР»
    next_test_bid_minor: int | None  # РєРѕРїРµР№РєРё
    currency: str
    current_mode: str | None
    current_cycle_started_at: datetime | None
    test_started_at: datetime | None
    main_started_at: datetime | None
    test_share: float | None
    target_test_impressions: int | None
    target_test_observation_minutes: int | None
    target_main_impressions: int | None
    target_main_observation_minutes: int | None
    min_bid_distance_minor: int | None  # Копейки, мин. шаг между тестовыми ставками
    test_impressions: int | None
    main_impressions: int | None
    test_elapsed_minutes: int | None
    main_elapsed_minutes: int | None
    covered_points_count: int   # покрытые точки текущего цикла (порог test)
    bid_points_total: int  # всего точек за отчётный день (диагностика)
    bid_points: list[BidPointStatsDTO]  # агрегаты за отчётный день (диагностика)
    cycle_covered_points_count: int  # дубль covered_points_count для совместимости
    cycle_bid_points: list[BidPointStatsDTO]   # агрегаты от current_cycle_started_at
    last_reason: str | None
    warnings: list[str]
    optimization_metric: OptimizationMetric  # CPC или CTR — текущая метрика оптимизации
    fact_cpo: float | None  # фактическое CPO кампании
    resolve_cpo: float | None  # resolve/target CPO кампании
    coverage_first_available_bucket_start: datetime | None = None
    coverage_current_layer: int | None = None
    coverage_undercovered_count: int | None = None
    coverage_selected_next_test_bid_minor: int | None = None
    coverage_bid_rows: list[CoverageLayerBidDTO] = field(
        default_factory=lambda: cast(list[CoverageLayerBidDTO], [])
    )
    best_plan_bid_minor: int | None = None
    fresh_best_main_bid_minor: int | None = None
    fresh_next_test_bid_minor: int | None = None
    recommended_main_bid_minor: int | None = None
    qualified_tested_bids_count: int | None = None
    recommended_next_test_bid_minor: int | None = None
    expected_enforced_bid_minor: int | None = None
    primary_status: str | None = None
    bid_sync_detail: str | None = None
    # New diagnostics fields
    best_cpo_bid_rub: float | None = None
    current_bid_rub: float | None = None
    expected_bid_rub: float | None = None
    selected_cpo_rub: float | None = None
    bid_sync_status: str | None = None
    unavailable_reason: str | None = None
    can_count_progress: bool = False
    main_target_explanation: str | None = None
    rec_bid_recommendation: dict[str, object] | None = None
    legacy_cycle_next_test_bid_minor: int | None = None
    state_updated_at: datetime | None = None
    auto_shelf_bid_control_strategy: AutoShelfBidControlStrategy = (
        AutoShelfBidControlStrategy.PLAN_DISTANCE
    )
    retest_interval_days: int = 7
