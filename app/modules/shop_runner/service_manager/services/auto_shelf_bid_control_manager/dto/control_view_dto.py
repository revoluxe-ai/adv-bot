"""DTO экрана Telegram для Auto Shelf Bid Control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BidPointStatsDTO:
    """Статистика по одной точке ставки для отображения в Telegram."""

    bid_minor: int  # копейки (как в CH auto_shelf_bid_intervals)
    currency: str
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
    """Срез состояния control-модуля для Telegram-экрана."""

    nmid: int
    auto_adv_id: int | None
    enabled: bool
    has_settings: bool
    has_state: bool
    dry_run: bool  # глобально: settings.AUTO_SHELF_BID_CONTROL_DRY_RUN
    bid_units_confirmed: bool
    actual_bid_minor: int | None  # копейки, Redis recommendations
    min_bid_minor: int | None  # копейки, мин. ставка WB (из min_bids cache)
    max_bid_minor: int | None  # копейки, настройка пользователя
    current_main_bid_minor: int | None  # копейки
    current_test_bid_minor: int | None  # копейки
    best_bid_minor: int | None  # копейки
    next_test_bid_minor: int | None  # копейки
    currency: str
    current_mode: str | None
    current_cycle_started_at: datetime | None
    test_started_at: datetime | None
    main_started_at: datetime | None
    test_share: float | None
    target_test_impressions: int | None
    target_main_impressions: int | None
    min_bid_distance_minor: int | None  # копейки, мин. шаг между тестовыми ставками
    test_impressions: int | None
    main_impressions: int | None
    covered_points_count: int
    bid_points: list[BidPointStatsDTO]
    last_reason: str | None
    warnings: list[str]

