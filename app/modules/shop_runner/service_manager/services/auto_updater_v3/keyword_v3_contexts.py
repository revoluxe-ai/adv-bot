"""Сборка ``KeywordV3Context`` для V3: orchestrator, UI loader, ladder view.

Вынесено из ``orchestrator`` во избежание циклических импортов с ``keyword_v3_ladder_view``.
"""

from __future__ import annotations

import logging

from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

logger = logging.getLogger(__name__)


def build_keyword_v3_contexts(
    keywords: list[CalculatedKeyword],
    raw_profiles: dict[str, list[BidPosition]],
) -> list[KeywordV3Context]:
    """Собрать контексты ключей с ``position_profile`` из WB bid profiles CH."""
    contexts: list[KeywordV3Context] = []
    for kw in keywords:
        bids = resolve_keyword_bid_profile(raw_profiles, kw.text)
        profile = profile_points_from_bid_positions(bids) if bids else None
        merged = kw.model_copy(update={"position_profile": profile})
        contexts.append(KeywordV3Context(keyword=merged, position_profile=profile))
    return contexts


async def load_campaign_v3_contexts(
    complex_adv: ComplexAdv,
    raw_profiles: dict[str, list[BidPosition]],
) -> list[KeywordV3Context]:
    """Контексты всех ключей РК на тике V3 — strict Redis (``get_keywords``).

    Raises:
        ShopRunnerKeywordsCacheMissError: hash в Redis отсутствует.
    """
    keywords = await complex_adv.get_keywords()
    return build_keyword_v3_contexts(keywords, raw_profiles)


async def load_campaign_v3_contexts_from_database(
    complex_adv: ComplexAdv,
    raw_profiles: dict[str, list[BidPosition]],
) -> list[KeywordV3Context]:
    """Контексты для Telegram UI — пересчёт из БД, не из Redis-кеша."""
    from app.modules.wb_adv_updater.keywords_access import fetch_keywords_from_database

    keywords = await fetch_keywords_from_database(complex_adv)
    return build_keyword_v3_contexts(keywords, raw_profiles)
