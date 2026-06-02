"""Маппинг ``CalculatedKeyword`` → ``CalculatedKeywordSnapshotDTO``.

Исключаем из snapshot: ``KeywordSettingDTO``, ``KeywordStat``, ``KeywordState``,
``KeywordCpmSources``, ``position_profile`` — только scalar-поля для consumers.
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.snapshot_data_updater.dto import CalculatedKeywordSnapshotDTO


def strategy_mode_to_snapshot_str(
    mode: KeywordStrategyMode | int | None,
) -> str | None:
    """``KeywordStrategyMode`` — ``IntEnum``; в snapshot храним имя, не ``.value`` (0,1,…)."""
    if mode is None:
        return None
    if isinstance(mode, KeywordStrategyMode):
        return mode.name
    try:
        return KeywordStrategyMode(int(mode)).name
    except (ValueError, TypeError):
        return str(mode)


def calculated_keyword_to_snapshot(kw: CalculatedKeyword) -> CalculatedKeywordSnapshotDTO:
    """Один keyword → slim DTO для ``AdvDataSnapshotDTO.keywords``."""
    cpm_sources = kw.cpm_sources
    return CalculatedKeywordSnapshotDTO(
        text=kw.text,
        adv_id=kw.adv_id,
        status=kw.status,
        status_reason=kw.reason,
        rating=kw.rating,
        resolved_cpm=kw.cpm,
        target_pay_for_order=kw.target_pay_for_order,
        above_rec_conversion=kw.above_rec_conversion,
        views=kw.views,
        clicks=kw.clicks,
        orders=kw.orders,
        spend=kw.spend,
        keyword_setting_original_id=kw.keyword_setting_original_id,
        cluster_text=kw.cluster_stat.text,
        hard_status=int(kw.hard_status) if kw.hard_status is not None else None,
        strategy_mode=strategy_mode_to_snapshot_str(kw.strategy_mode),
        target_place=kw.target_place,
        position=kw.position,
        conv_views_to_orders=kw.conv_views_to_orders,
        orders_per_1000_rub=kw.orders_per_1000_rub,
        pay_for_order=kw.pay_for_order,
        cpm_set_bid=kw.cpm_set_bid,
        cpm_from_bid_log=kw.cpm_from_bid_log,
        cpm_from_stats=kw.cpm_from_stats,
        predict_ctr=kw.predict_ctr,
        added_clicks=kw.added_clicks,
        relevant=kw.relevant,
        timestamp=kw.timestamp,
        total_views=kw.total_views,
        total_orders=kw.total_orders,
        cpm_from_api=cpm_sources.cpm_from_api if cpm_sources else None,
    )


def calculated_keywords_to_snapshots(
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeywordSnapshotDTO]:
    """Пакетный маппинг списка keywords."""
    return [calculated_keyword_to_snapshot(kw) for kw in keywords]
