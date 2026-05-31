"""Синхронизация ``KeywordSetting.target_place`` для V3 по профилю ставок CH.

Вызывается из ``process_adv_v3`` на каждом тике (``finally``), если включён individual mode.
Корутина ``update_individual_keyword_target_places`` для V3 не используется (только V2).

``target_place`` берётся из ``ModeCandidate.position`` (лестница V3), а не из legacy-предиктора
``build_mode_candidates`` / ``resolve_v3_target_place`` (MIN по CPO заказа V2).
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
    moc_equality_flags,
    resolve_v3_target_place,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
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

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_is_managed(hard_status: int) -> bool:
    """Auto (1) или white-list (2): V3 может менять ``target_place`` при force-zero."""
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def _effective_strategy_mode(
    keyword: KeywordSetting,
    calc_kw: CalculatedKeyword | None,
) -> KeywordStrategyMode:
    """Режим для target_place: из ``CalculatedKeyword`` тика (как UI), иначе из БД."""
    if calc_kw is not None:
        return calc_kw.keyword_setting.strategy_mode
    return keyword.strategy_mode


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
    force_all_target_place_zero: bool = False,
    target_place_fallback_zero_by_keyword_id: dict[int, bool] | None = None,
) -> None:
    """Пересчёт ``target_place`` для всех ключей РК по профилю и ``strategy_mode``.

    ``strategy_mode`` берётся из ``calculated_by_text`` (ledger/Redis тика), не из устаревшей
    строки ``KeywordSetting``, чтобы ``target_place`` совпадал с профилем V3 в UI.

    Args:
        force_all_target_place_zero: CAMPAIGN_NO_DATA — min bid (0) для **управляемых** ключей.
        target_place_fallback_zero_by_keyword_id: CAMPAIGN_NORMAL — ``ks_id → force 0``
            для NO_CH tier (в т.ч. пока ключ ещё OFF).
    """
    stmt = select(KeywordSetting).where(
        KeywordSetting.adv_setting_id == adv.adv_setting_original_id
    )
    from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
        load_campaign_orders_per_cart_7d,
        resolve_orders_per_cart_for_cpo,
    )

    campaign_orders_per_cart_7d = await load_campaign_orders_per_cart_7d(
        adv.complex_adv.adv_setting
    )

    moc_stats: dict[str, int] = {
        "with_ladder": 0,
        "o_eq_c": 0,
        "o_eq_m": 0,
        "o_ne_c": 0,
        "skipped_no_profile": 0,
    }

    async with sm(read_only=False) as session:
        result: Result[tuple[KeywordSetting]] = await session.execute(stmt)
        keywords = result.scalars().all()
        for keyword in keywords:
            profile = resolve_keyword_bid_profile(bid_profiles, keyword.text)
            calc_kw = _calculated_keyword_lookup(calculated_by_text, keyword.text)
            strategy_mode = _effective_strategy_mode(keyword, calc_kw)
            hard_status = int(keyword.hard_status)

            ks_id = int(keyword.id)
            fallback_zero = (
                target_place_fallback_zero_by_keyword_id is not None
                and target_place_fallback_zero_by_keyword_id.get(ks_id, False)
            )

            if force_all_target_place_zero:
                if not _hard_status_is_managed(hard_status):
                    continue
                keyword.target_place = NO_DATA_TARGET_PLACE_FALLBACK
                continue

            if fallback_zero:
                if not _hard_status_is_managed(hard_status):
                    continue
                keyword.target_place = NO_DATA_TARGET_PLACE_FALLBACK
                continue

            no_v2_cpo = (
                calc_kw is None or keyword_v2_pay_for_order_unavailable(calc_kw)
            )
            if not profile or no_v2_cpo:
                moc_stats["skipped_no_profile"] += 1
                if (
                    strategy_mode == KeywordStrategyMode.OFF
                    and no_v2_cpo
                ):
                    keyword.target_place = None
                elif _hard_status_is_managed(hard_status):
                    logger.warning(
                        "No bid profile or no V2 CPO for keyword %s, adv_id=%s; "
                        "target_place=%s (min bid)",
                        keyword.text,
                        adv.adv_id,
                        NO_DATA_TARGET_PLACE_FALLBACK,
                    )
                    keyword.target_place = NO_DATA_TARGET_PLACE_FALLBACK
                else:
                    keyword.target_place = None
                continue
            assert calc_kw is not None
            profile_points = profile_points_from_bid_positions(profile)
            orders_per_cart = resolve_orders_per_cart_for_cpo(
                campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                key_orders=calc_kw.orders,
                key_carts=calc_kw.add_to_cart,
            )
            if orders_per_cart is None:
                orders_per_cart = campaign_orders_per_cart_7d
            candidates = build_mode_candidates(
                profile=profile_points,
                keyword_text=keyword.text,
                conv_views_to_orders=(
                    calc_kw.conv_views_to_orders
                    if orders_per_cart is None
                    else None
                ),
                orders_per_cart=orders_per_cart,
            )
            o_eq_c, o_eq_m = moc_equality_flags(
                candidates[AggressionTargetMode.MIN_CPA],
                candidates[AggressionTargetMode.OPTIMUM],
                candidates[AggressionTargetMode.MAX_CONVERSION],
            )
            moc_stats["with_ladder"] += 1
            if o_eq_c:
                moc_stats["o_eq_c"] += 1
            else:
                moc_stats["o_ne_c"] += 1
            if o_eq_m:
                moc_stats["o_eq_m"] += 1

            resolved = resolve_v3_target_place(strategy_mode, candidates)
            if resolved is None:
                if strategy_mode == KeywordStrategyMode.OFF:
                    keyword.target_place = None
                else:
                    logger.warning(
                        "Invalid V3 candidate for keyword %s mode=%s, adv_id=%s; "
                        "target_place=%s (min bid)",
                        keyword.text,
                        strategy_mode.name,
                        adv.adv_id,
                        NO_DATA_TARGET_PLACE_FALLBACK,
                    )
                    keyword.target_place = NO_DATA_TARGET_PLACE_FALLBACK
            else:
                keyword.target_place = resolved
        await session.commit()

    n = moc_stats["with_ladder"]
    if n > 0:
        logger.info(
            "v3 campaign MOC stats adv_id=%s with_ladder=%s o_eq_c=%s (%.1f%%) "
            "o_eq_m=%s (%.1f%%) o_ne_c=%s skipped_no_profile=%s rk=%s",
            adv.adv_id,
            n,
            moc_stats["o_eq_c"],
            100.0 * moc_stats["o_eq_c"] / n,
            moc_stats["o_eq_m"],
            100.0 * moc_stats["o_eq_m"] / n,
            moc_stats["o_ne_c"],
            moc_stats["skipped_no_profile"],
            campaign_orders_per_cart_7d,
        )
