"""AutoUpdater v3 orchestration (per-keyword aggression).

Phase 0: gap-rebalance (БС, MIN_CPO) — всегда при наличии WBAdvDTO, до plan/fact cache.
Phase 1: plan/fact, ``SalesStates``, ``select_v3_actions``.

Один fetch ``get_keyword_bid_profiles`` на цикл; ``target_place`` — на каждом тике (``finally``).
Наблюдаемость: ``v3_selection`` и ``docks/V3_UPDATER_VALIDATION.md``.
"""

from __future__ import annotations

import logging

from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    compute_resolve_cost_threshold,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    select_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync import (
    sync_keyword_target_places_v3,
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
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO

logger = logging.getLogger(__name__)


def build_keyword_v3_contexts(
    keywords: list[CalculatedKeyword],
    raw_profiles: dict[str, list[BidPosition]],
) -> list[KeywordV3Context]:
    """Собрать контексты ключей с position_profile из WB bid profiles."""
    contexts: list[KeywordV3Context] = []
    for kw in keywords:
        bids = resolve_keyword_bid_profile(raw_profiles, kw.text)
        profile = profile_points_from_bid_positions(bids) if bids else None
        merged = kw.model_copy(update={"position_profile": profile})
        contexts.append(KeywordV3Context(keyword=merged, position_profile=profile))
    return contexts


async def _load_v3_wb_context(
    complex_adv: ComplexAdv,
    *,
    wb_shop_data_manager: WBShopDataManager,
) -> tuple[WBAdvDTO | None, dict[str, list[BidPosition]]]:
    """Один запрос WBAdvDTO + bid profiles на цикл V3 (CH)."""
    shelf_active = complex_adv.shelf_promotion_active
    if shelf_active:
        await TrafficClicksManager().enrich(complex_adv)

    wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
    if not wb_dtos:
        return None, {}

    dto = wb_dtos[0]
    nmid = dto.main_nmid
    if dto.search_adv_min_bids.get(nmid) is None:
        logger.warning(
            "[adv_id=%s] v3: min_bid cache miss for nmid=%s, backfill Redis/WB",
            complex_adv.adv_id,
            nmid,
        )
        if await wb_shop_data_manager.backfill_min_bids_for_adv(complex_adv):
            wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
            if wb_dtos:
                dto = wb_dtos[0]
        else:
            logger.error(
                "[adv_id=%s] v3: min_bid backfill failed for nmid=%s",
                complex_adv.adv_id,
                nmid,
            )

    predictor = build_predict_keywords_target_place()
    raw_profiles = await predictor.get_keyword_bid_profiles(
        dto, dto.min_target_position
    )
    return dto, raw_profiles


async def _safe_sync_target_places_v3(
    complex_adv: ComplexAdv,
    dto: WBAdvDTO,
    raw_profiles: dict[str, list[BidPosition]],
) -> None:
    """Best-effort sync ``target_place`` в ``finally`` без подмены ошибки из ``try``.

    Зачем отдельная обёртка, а не прямой вызов ``sync_keyword_target_places_v3`` в
    ``finally``: блок ``finally`` выполняется всегда (успех, ранний return, сбой
    phase0/apply). Нам нужно на каждом тике попытаться записать свежие
    ``target_place`` в БД. Если sync падает (БД, сеть), исключение **нельзя**
    пробрасывать из ``finally`` — иначе Python подменит исходную ошибку из ``try``
    (PEP 409) и в логах/алертах будет не та причина. Поэтому здесь только ERROR-лог
    и подавление ошибки sync; основной сбой цикла по-прежнему уходит наверх.
    """
    try:
        await sync_keyword_target_places_v3(dto, raw_profiles)
    except Exception:
        logger.error(
            "[adv_id=%s] v3: target_place sync failed in finally "
            "(original try exception preserved, not re-raised)",
            complex_adv.adv_id,
            exc_info=True,
        )


async def _run_phase0_gap_rebalance(
    complex_adv: ComplexAdv,
    *,
    keywords: list[CalculatedKeyword],
    contexts: list[KeywordV3Context],
    dto: WBAdvDTO | None,
) -> tuple[list[CalculatedKeyword], bool]:
    """Gap-rebalance до plan/fact; возвращает актуальный список ключей и флаг apply."""
    if dto is None:
        return keywords, False

    shelf_active = complex_adv.shelf_promotion_active
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
        return await complex_adv.get_keywords(), True
    return keywords, False


async def process_adv_v3(
    complex_adv: ComplexAdv,
    *,
    wb_shop_data_manager: WBShopDataManager,
    max_last_period: int = 2,
) -> None:
    """Run v3 cycle for one campaign (gap-rebalance, then plan/fact/state)."""
    adv = complex_adv.adv_setting
    keywords = await complex_adv.get_keywords()

    dto, raw_profiles = await _load_v3_wb_context(
        complex_adv, wb_shop_data_manager=wb_shop_data_manager
    )
    try:
        contexts = build_keyword_v3_contexts(keywords, raw_profiles)

        keywords, phase0_changed = await _run_phase0_gap_rebalance(
            complex_adv,
            keywords=keywords,
            contexts=contexts,
            dto=dto,
        )
        if phase0_changed:
            contexts = build_keyword_v3_contexts(keywords, raw_profiles)

        plan = AdvSettingAutoUpdater.get_plan_data(adv)
        if not plan:
            logger.debug("[adv_id=%s] v3: no plan, skip", complex_adv.adv_id)
            return

        updater = AdvSettingAutoUpdater(adv, max_last_period)
        fact = await updater.get_fact_data(keywords)

        plan_fact_change = ChangePlanFact(adv)
        plan_fact_equal = await plan_fact_change.check_equal_in_cache(plan, fact)
        if plan_fact_equal:
            logger.debug("[adv_id=%s] v3: plan/fact unchanged, skip", complex_adv.adv_id)
            return

        async def cache_plan_fact_snapshot() -> None:
            """Зафиксировать plan/fact после решения по метрикам (state/действия)."""
            await plan_fact_change.set_new_plan_fact(plan, fact)

        state: SalesStates | None = detect_campaign_state(plan, fact)
        if state is None:
            logger.warning(
                "[adv_id=%s] v3: insufficient data for state", complex_adv.adv_id
            )
            await cache_plan_fact_snapshot()
            return

        if dto is None:
            logger.warning(
                "[adv_id=%s] v3: no WBAdvDTO, plan/fact cache not updated (retry next cycle)",
                complex_adv.adv_id,
            )
            return

        shelf_active = complex_adv.shelf_promotion_active

        actions = select_v3_actions(
            state=state,
            contexts=contexts,
            shelf_promotion_active=shelf_active,
            rollout_aggressiveness=complex_adv.v3_rollout_aggressiveness,
            shelf_click_mode=resolve_shelf_click_mode_from_adv(complex_adv)
            if shelf_active
            else None,
            plan_max_pay_for_order=float(plan.max_pay_for_order),
            plan=plan,
            fact=fact,
        )
        await apply_v3_actions(actions, complex_adv=complex_adv)

        await cache_plan_fact_snapshot()
        up_count = sum(1 for a in actions if a.action.value == "UP")
        down_count = sum(1 for a in actions if a.action.value == "DOWN")
        force_off_count = sum(1 for a in actions if a.action.value == "FORCE_OFF")
        m1_count = sum(1 for a in actions if a.reason.startswith("m1_"))
        m2_count = sum(1 for a in actions if a.reason.startswith("m2_"))
        m3_count = sum(1 for a in actions if a.reason.startswith("m3_"))
        logger.info(
            "[adv_id=%s] v3_cycle state=%s resolve=%s fact_cpa=%s up=%s down=%s off=%s m1=%s m2=%s m3=%s",
            complex_adv.adv_id,
            state.name,
            compute_resolve_cost_threshold(plan, fact),
            fact.pay_for_order,
            up_count,
            down_count,
            force_off_count,
            m1_count,
            m2_count,
            m3_count,
        )
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
    finally:
        # Best-effort target_place; сбой sync не маскирует исключение из try (см. _safe_sync_*).
        if dto is not None and complex_adv.individual_keywords_target_place_mode:
            await _safe_sync_target_places_v3(complex_adv, dto, raw_profiles)
