"""AutoUpdater v3 orchestration (per-keyword aggression).

Phase 0: gap-rebalance (БС, MIN_CPO) — всегда при наличии WBAdvDTO, до plan/fact cache.
Phase 1: plan/fact, ``SalesStates``, ``select_v3_actions``.

Наблюдаемость: ``v3_selection`` и ``docks/V3_UPDATER_VALIDATION.md``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.plan_fact_change_redis_caches import (
    ChangePlanFact,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
    detect_campaign_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
    resolve_shelf_click_mode_from_adv,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    apply_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rebalance import (
    run_ladder_gap_rebalance_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    select_v3_actions,
)
from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
    TrafficClicksManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

logger = logging.getLogger(__name__)


def build_keyword_v3_contexts(
    keywords: list[CalculatedKeyword],
    raw_profiles: dict[str, Any],
) -> list[KeywordV3Context]:
    """Собрать контексты ключей с position_profile из WB bid profiles."""
    contexts: list[KeywordV3Context] = []
    for kw in keywords:
        bids = resolve_keyword_bid_profile(raw_profiles, kw.text)
        profile = profile_points_from_bid_positions(bids) if bids else None
        merged = kw.model_copy(update={"position_profile": profile})
        contexts.append(KeywordV3Context(keyword=merged, position_profile=profile))
    return contexts


async def _run_phase0_gap_rebalance(
    complex_adv: ComplexAdv,
    *,
    keywords: list[CalculatedKeyword],
    wb_shop_data_manager: WBShopDataManager,
) -> list[CalculatedKeyword]:
    """Gap-rebalance до plan/fact; возвращает актуальный список ключей."""
    shelf_active = complex_adv.shelf_promotion_active
    if shelf_active:
        await TrafficClicksManager().enrich(complex_adv)

    wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
    if not wb_dtos:
        logger.debug(
            "[adv_id=%s] v3 gap rebalance: no WBAdvDTO, skip",
            complex_adv.adv_id,
        )
        return keywords

    dto = wb_dtos[0]
    predictor = build_predict_keywords_target_place()
    raw_profiles = await predictor.get_keyword_bid_profiles(
        dto, dto.min_target_position
    )
    contexts = build_keyword_v3_contexts(keywords, raw_profiles)
    click_mode = (
        resolve_shelf_click_mode_from_adv(complex_adv)
        if shelf_active
        else ShelfClickMode.UNKNOWN
    )
    changed = await run_ladder_gap_rebalance_v3(
        complex_adv,
        contexts=contexts,
        shelf_promotion_active=shelf_active,
        shelf_click_mode=click_mode,
        rollout_aggressiveness=complex_adv.v3_rollout_aggressiveness,
    )
    if changed:
        return await complex_adv.get_keywords()
    return keywords


async def process_adv_v3(
    complex_adv: ComplexAdv,
    *,
    wb_shop_data_manager: WBShopDataManager,
    max_last_period: int = 2,
) -> None:
    """Run v3 cycle for one campaign (gap-rebalance, then plan/fact/state)."""
    adv = complex_adv.adv_setting
    keywords = await complex_adv.get_keywords()
    keywords = await _run_phase0_gap_rebalance(
        complex_adv,
        keywords=keywords,
        wb_shop_data_manager=wb_shop_data_manager,
    )

    plan = AdvSettingAutoUpdater.get_plan_data(adv)
    if not plan:
        logger.debug("[adv_id=%s] v3: no plan, skip", complex_adv.adv_id)
        return

    updater = AdvSettingAutoUpdater(adv, max_last_period)
    fact = await updater.get_fact_data(keywords)

    plan_fact_change = ChangePlanFact(adv)
    if await plan_fact_change.check_equal_in_cache(plan, fact):
        logger.debug("[adv_id=%s] v3: plan/fact unchanged, skip", complex_adv.adv_id)
        return

    async def cache_plan_fact_snapshot() -> None:
        """Зафиксировать plan/fact после решения по метрикам (state/действия)."""
        await plan_fact_change.set_new_plan_fact(plan, fact)

    state = detect_campaign_state(plan, fact)
    if state is None:
        logger.info("[adv_id=%s] v3: insufficient data for state", complex_adv.adv_id)
        await cache_plan_fact_snapshot()
        return
    if state == SalesStates.OPTIMAL:
        logger.info("[adv_id=%s] v3: OPTIMAL, no actions", complex_adv.adv_id)
        await cache_plan_fact_snapshot()
        return

    shelf_active = complex_adv.shelf_promotion_active
    if shelf_active:
        await TrafficClicksManager().enrich(complex_adv)

    wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
    if not wb_dtos:
        logger.warning(
            "[adv_id=%s] v3: no WBAdvDTO, plan/fact cache not updated (retry next cycle)",
            complex_adv.adv_id,
        )
        return
    dto = wb_dtos[0]
    predictor = build_predict_keywords_target_place()
    raw_profiles = await predictor.get_keyword_bid_profiles(
        dto, dto.min_target_position
    )
    contexts = build_keyword_v3_contexts(keywords, raw_profiles)

    actions = select_v3_actions(
        state=state,
        contexts=contexts,
        shelf_promotion_active=shelf_active,
        rollout_aggressiveness=complex_adv.v3_rollout_aggressiveness,
        shelf_click_mode=resolve_shelf_click_mode_from_adv(complex_adv)
        if shelf_active
        else None,
        plan_max_pay_for_order=float(plan.max_pay_for_order),
    )
    await apply_v3_actions(actions)

    await cache_plan_fact_snapshot()
    for act in actions:
        sel = act.selection_log
        if sel is not None:
            logger.info(
                "[adv_id=%s] v3_selection state=%s action=%s reason=%s "
                "pool=%s pool_after_rec=%s tier=%s state_cost=%s %s->%s move=%s imputed=%s",
                complex_adv.adv_id,
                state.name,
                act.action.value,
                act.reason,
                sel.pool_size,
                sel.pool_size_after_rec,
                sel.rec_tier,
                sel.state_cost,
                sel.from_mode,
                sel.to_mode,
                sel.move_kind,
                sel.imputed,
            )
    logger.info(
        "[adv_id=%s] v3: state=%s actions=%s",
        complex_adv.adv_id,
        state.name,
        [a.model_dump() for a in actions],
    )
