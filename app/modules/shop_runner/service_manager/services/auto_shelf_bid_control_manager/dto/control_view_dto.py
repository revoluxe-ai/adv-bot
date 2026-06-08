"""DTO СЌРєСЂР°РЅР° Telegram РґР»СЏ Auto Shelf Bid Control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .optimization_metric import OptimizationMetric


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
class AutoShelfBidControlViewDTO:
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
    min_bid_distance_minor: int | None  # РєРѕРїРµР№РєРё, РјРёРЅ. С€Р°Рі РјРµР¶РґСѓ С‚РµСЃС‚РѕРІС‹РјРё СЃС‚Р°РІРєР°РјРё
    test_impressions: int | None
    main_impressions: int | None
    test_elapsed_minutes: int | None
    main_elapsed_minutes: int | None
    covered_points_count: int  # РїРѕРєСЂС‹С‚С‹Рµ С‚РѕС‡РєРё С‚РµРєСѓС‰РµРіРѕ С†РёРєР»Р° (РїРѕСЂРѕРі test)
    bid_points_total: int  # РІСЃРµРіРѕ С‚РѕС‡РµРє Р·Р° РѕС‚С‡С‘С‚РЅС‹Р№ РґРµРЅСЊ (РґРёР°РіРЅРѕСЃС‚РёРєР°)
    bid_points: list[BidPointStatsDTO]  # Р°РіСЂРµРіР°С‚С‹ Р·Р° РѕС‚С‡С‘С‚РЅС‹Р№ РґРµРЅСЊ (РґРёР°РіРЅРѕСЃС‚РёРєР°)
    cycle_covered_points_count: int  # РґСѓР±Р»СЊ covered_points_count РґР»СЏ СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚Рё
    cycle_bid_points: list[BidPointStatsDTO]  # Р°РіСЂРµРіР°С‚С‹ РѕС‚ current_cycle_started_at
    last_reason: str | None
    warnings: list[str]
    optimization_metric: OptimizationMetric  # CPC РёР»Рё CTR вЂ” С‚РµРєСѓС‰Р°СЏ РјРµС‚СЂРёРєР° РѕРїС‚РёРјРёР·Р°С†РёРё
    fact_cpo: float | None  # С„Р°РєС‚РёС‡РµСЃРєРѕРµ CPO РєР°РјРїР°РЅРёРё
    resolve_cpo: float | None  # resolve/target CPO РєР°РјРїР°РЅРёРё
    rec_bid_recommendation: dict[str, object] | None = None


