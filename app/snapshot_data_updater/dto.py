"""Pydantic-DTO снимка рекламных данных магазина.

Назначение
----------
Slim-представления для слоя ``snapshot_data_updater``. Сериализуются в Redis
(новый namespace ``adv_snapshot:v1:...``). **Не** дублируют целиком
``CalculatedKeyword``, ``KeywordSettingDTO``, ``KeywordStat`` — только поля,
нужные consumer'ам (``update_cluster_bids``, ``get_wb_advs_dto``).

Иерархия
--------
``ShopAdvSnapshotBatchDTO`` (один shop, один tick)
  └── ``AdvDataSnapshotDTO`` (одна active РК)
        ├── ``AdvSettingsSnapshotDTO`` (PG)
        ├── ``PlanFactSnapshotDTO`` (CH)
        ├── ``CalculatedKeywordSnapshotDTO[]`` (Redis / warmup)
        ├── ``MinBidsSnapshotDTO`` (Redis v2)
        ├── ``ClusterTextsSnapshotDTO`` (CH, search adv)
        └── ``SnapshotDiagnostics`` (cache hit, warmup, ошибки секций)
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)

KeywordsSource = Literal[
    "redis_hit",
    "redis_unknown_freshness",
    "redis_stale",
    "recalculated",
    "missing",
    "error",
]
"""Откуда взяты keywords в snapshot (для cutover/fallback)."""


class FreshnessSnapshotDTO(BaseModel):
    """Метаданные свежести одной секции снимка (keywords, min_bids, …)."""

    warmed_at: datetime | None = None
    age_sec: float | None = None
    is_fresh: bool = False
    source: str | None = None


class MinBidCellDTO(BaseModel):
    """Пропущенная ячейка min_bids v2: (adv_id WB, placement, nmid)."""

    adv_id: int
    placement: str
    nmid: int


class CalculatedKeywordSnapshotDTO(BaseModel):
    """Slim-ключ для snapshot; маппинг из ``CalculatedKeyword`` — ``keyword_mapper``."""

    text: str
    adv_id: int
    status: KeywordStatus
    status_reason: KeywordStatusReason | None = None
    rating: float | None = None
    resolved_cpm: float | None = None
    target_pay_for_order: float | None = None
    above_rec_conversion: bool | None = None
    views: int = 0
    clicks: int = 0
    orders: int = 0
    spend: float = 0.0
    keyword_setting_original_id: int | None = None
    cluster_text: str | None = None
    hard_status: int | None = None
    strategy_mode: str | None = None
    target_place: int | None = None
    position: float | None = None
    conv_views_to_orders: float | None = None
    orders_per_1000_rub: float | None = None
    pay_for_order: float | None = None
    cpm_set_bid: int | None = None
    cpm_from_bid_log: float | None = None
    cpm_from_stats: float | None = None
    cpm_from_api: int | None = None
    predict_ctr: float | None = None
    added_clicks: int = 0
    relevant: bool | None = None
    timestamp: datetime | None = None
    total_views: int | None = None
    total_orders: int | None = None


class AdvSettingsSnapshotDTO(BaseModel):
    """Настройки кампании из Postgres без ORM (для assembler и adapters)."""

    adv_id: int
    shop_id: str
    nm_id: int | None = None
    nmids: list[int] = Field(default_factory=list)
    search_adv_id: int | None = None
    bot_active: bool = True
    active_status: str | None = None
    bidder_active: bool | None = None


class PlanFactSnapshotDTO(BaseModel):
    """Агрегат plan/fact из ``plan_fact_stats`` (ClickHouse) на момент сбора."""

    adv_id: int
    plan_views: float | None = None
    fact_views: float | None = None
    plan_orders: float | None = None
    fact_orders: float | None = None
    fact_predict_orders: float | None = None
    fact_pay_for_order: float | None = None
    fact_method: str | None = None


class MinBidsSnapshotDTO(BaseModel):
    """Снимок min_bids v2: coverage по ячейкам auto/search × nmid."""

    adv_id: int
    bids_by_cluster: dict[str, int] = Field(default_factory=dict)
    search_by_nmid: dict[int, int] = Field(default_factory=dict)
    auto_by_nmid: dict[int, int] = Field(default_factory=dict)
    requested_cells: int = 0
    hit_cells: int = 0
    missing_cells: list[MinBidCellDTO] = Field(default_factory=list)
    coverage_ratio: float = 0.0
    cache_hit: bool = False
    freshness: FreshnessSnapshotDTO | None = None


class ClusterTextsSnapshotDTO(BaseModel):
    """Множество norm_query из CH для auction (search) adv_id — input cluster_bids."""

    auction_adv_id: int
    texts: set[str] = Field(default_factory=set)


class KeywordsWarmupDiagnostics(BaseModel):
    """Как были получены keywords: cache hit, stale, пересчёт warmup, ошибка."""

    keywords_freshness: FreshnessSnapshotDTO | None = None
    keywords_cache_hit: bool = False
    keywords_cache_stale: bool = False
    keywords_warmed_by_snapshot_updater: bool = False
    keywords_warmup_duration_ms: float | None = None
    keywords_count: int = 0
    keywords_error: str | None = None
    keywords_source: KeywordsSource = "missing"


class SnapshotDiagnostics(BaseModel):
    """Счётчики collector и диагностика секций одного adv-снимка."""

    keywords_cache_hit: bool = False
    keywords: KeywordsWarmupDiagnostics = Field(
        default_factory=KeywordsWarmupDiagnostics
    )
    tasks_ok: int = 0
    tasks_failed: int = 0
    tasks_timeout: int = 0
    errors_by_section: dict[str, str] = Field(default_factory=dict)


class AdvDataSnapshotDTO(BaseModel):
    """Полный read-only снимок одной рекламной кампании."""

    adv_id: int
    shop_id: str
    collected_at: datetime
    expires_at: datetime | None = None
    schema_version: int = 1
    partial: bool = False
    section_completeness: dict[str, bool] = Field(default_factory=dict)
    settings: AdvSettingsSnapshotDTO
    plan_fact: PlanFactSnapshotDTO | None = None
    keywords: list[CalculatedKeywordSnapshotDTO] = Field(default_factory=list)
    min_bids: MinBidsSnapshotDTO | None = None
    cluster_texts: ClusterTextsSnapshotDTO | None = None
    diagnostics: SnapshotDiagnostics = Field(default_factory=SnapshotDiagnostics)


class ShopAdvSnapshotBatchDTO(BaseModel):
    """Результат одного ``RefreshShopSnapshotTask`` / ``collect_shop`` — весь магазин."""

    shop_id: str
    collected_at: datetime
    schema_version: int = 1
    snapshots: list[AdvDataSnapshotDTO] = Field(default_factory=list)


class ShopCollectBundle(BaseModel):
    """Устаревший вспомогательный bundle; предпочтительно ``PostgresShopSnapshotLoad``."""

    shop_id: str
    settings: list[AdvSettingsSnapshotDTO] = Field(default_factory=list)
    warmup_adv_ids: list[int] = Field(default_factory=list)
