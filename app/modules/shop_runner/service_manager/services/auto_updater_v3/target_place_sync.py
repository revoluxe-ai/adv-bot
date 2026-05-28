"""Синхронизация ``KeywordSetting.target_place`` для V3 по профилю ставок CH.

Вызывается из ``process_adv_v3`` на каждом тике (``finally``), если включён individual mode.
Корутина ``update_individual_keyword_target_places`` для V3 не используется (только V2).

``target_place`` берётся из ``ModeCandidate.position`` (лестница V3), а не из legacy-предиктора
``get_target_position_for_strategy_mode`` (MIN по min корзине).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.engine import Result

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    target_place_for_v3_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    NO_DATA_TARGET_PLACE_FALLBACK,
    keyword_v2_pay_for_order_unavailable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


def _mode_for_target_place(strategy_mode: KeywordStrategyMode) -> KeywordStrategyMode:
    """Режим для расчёта позиции: OFF → MIN_CPA (нет кандидата OFF)."""
    if strategy_mode == KeywordStrategyMode.OFF:
        return KeywordStrategyMode.MIN_CPA
    return strategy_mode


def _calculated_keyword_lookup(
    calculated_by_text: dict[str, CalculatedKeyword] | None,
    keyword_text: str,
) -> CalculatedKeyword | None:
    """Найти ``CalculatedKeyword`` по тексту (lower-case ключ в map из orchestrator)."""
    if not calculated_by_text:
        return None
    key = keyword_text.lower()
    return calculated_by_text.get(key) or calculated_by_text.get(keyword_text)


async def sync_keyword_target_places_v3(
    adv: WBAdvDTO,
    bid_profiles: dict[str, list[BidPosition]],
    *,
    calculated_by_text: dict[str, CalculatedKeyword] | None = None,
) -> None:
    """Пересчёт ``target_place`` для всех ключей РК по профилю и ``strategy_mode``.

    Обновляются все ключи, включая OFF (для OFF позиция из профиля как для MIN_CPA).
    Нет CH-профиля, нет ``calculated_by_text`` / V2 CPO или invalid кандидат: для активных
    режимов — ``target_place=0`` (min bid WB); OFF — ``None``.
    """
    stmt = select(KeywordSetting).where(
        KeywordSetting.adv_setting_id == adv.adv_setting_original_id
    )
    async with sm(read_only=False) as session:
        result: Result[tuple[KeywordSetting]] = await session.execute(stmt)
        keywords = result.scalars().all()
        for keyword in keywords:
            profile = resolve_keyword_bid_profile(bid_profiles, keyword.text)
            calc_kw = _calculated_keyword_lookup(calculated_by_text, keyword.text)
            no_v2_cpo = (
                calc_kw is None
                or keyword_v2_pay_for_order_unavailable(calc_kw)
            )
            if not profile or no_v2_cpo:
                if keyword.strategy_mode == KeywordStrategyMode.OFF:
                    keyword.target_place = None
                else:
                    logger.warning(
                        "No bid profile or no V2 CPO for keyword %s, adv_id=%s; "
                        "target_place=%s (min bid)",
                        keyword.text,
                        adv.adv_id,
                        NO_DATA_TARGET_PLACE_FALLBACK,
                    )
                    keyword.target_place = NO_DATA_TARGET_PLACE_FALLBACK
                continue
            profile_points = profile_points_from_bid_positions(profile)
            candidates = build_mode_candidates(
                profile=profile_points,
                keyword_text=keyword.text,
                conv_views_to_orders=calc_kw.conv_views_to_orders,
            )
            calc_mode = _mode_for_target_place(keyword.strategy_mode)
            keyword.target_place = target_place_for_v3_strategy_mode(
                calc_mode,
                candidates,
            )
        await session.commit()
