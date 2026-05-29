"""AutoUpdater v3 orchestration (per-keyword aggression).

Порядок на **каждом** тике:
  1. CH bid profiles; plan/fact → ``detect_campaign_state``.
  2. Кампания ``NO_DATA`` (Н) или ``state is None`` — полный стоп (как V2).
  3. Иначе preamble: **M1** → **trim** (если ``fact.pay_for_order > plan.max``) →
     no_data (N-state ключей) → selector **M2/M3** (``OVERSPEND`` не режет gate).
  4. Нетто-flush ``strategy_mode`` + ``hard_status``; ``target_place`` после flush.

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    plan_no_data_activation_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    compute_resolve_cost_threshold,
    plan_campaign_trim_by_max_state_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    build_prepared_from_contexts,
    plan_m1_mass_cheap_promotion_with_plan_fact,
    select_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync import (
    sync_keyword_target_places_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
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


def _v3_campaign_ladder_blocked(state: SalesStates | None) -> bool:
    """Как ``AdvControlSystem``: без агрегата fact CPO по РК сценарий не крутим."""
    return state is None or state == SalesStates.NO_DATA


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


def _calculated_keywords_by_text(
    keywords: list[CalculatedKeyword],
) -> dict[str, CalculatedKeyword]:
    """Индекс ключей для V2 CPO в ``sync_keyword_target_places_v3``."""
    return {kw.text.lower(): kw for kw in keywords}


async def _safe_sync_target_places_v3(
    complex_adv: ComplexAdv,
    dto: WBAdvDTO,
    raw_profiles: dict[str, list[BidPosition]],
    *,
    keywords: list[CalculatedKeyword],
) -> None:
    """Best-effort sync ``target_place`` без подмены ошибки из ``try`` (PEP 409)."""
    try:
        await sync_keyword_target_places_v3(
            dto,
            raw_profiles,
            calculated_by_text=_calculated_keywords_by_text(keywords),
        )
    except Exception:
        logger.error(
            "[adv_id=%s] v3: target_place sync failed "
            "(original try exception preserved, not re-raised)",
            complex_adv.adv_id,
            exc_info=True,
        )


async def process_adv_v3(
    complex_adv: ComplexAdv,
    *,
    wb_shop_data_manager: WBShopDataManager,
    max_last_period: int = 2,
) -> None:
    """Один тик V3: in-memory ledger → нетто-flush → target_place."""
    adv = complex_adv.adv_setting
    keywords = await complex_adv.get_keywords()
    ledger = V3TickKeywordLedger.from_keywords(keywords)

    dto, raw_profiles = await _load_v3_wb_context(
        complex_adv, wb_shop_data_manager=wb_shop_data_manager
    )
    target_place_synced = False
    selector_actions_logged: list[V3Action] = []

    campaign_ladder_blocked = False

    async def _sync_target_places_once() -> None:
        """После flush; в finally — если тик оборвался раньше."""
        nonlocal target_place_synced
        if target_place_synced or campaign_ladder_blocked:
            return
        if dto is not None and complex_adv.individual_keywords_target_place_mode:
            await _safe_sync_target_places_v3(
                complex_adv, dto, raw_profiles, keywords=ledger.keywords
            )
            target_place_synced = True

    try:
        contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)

        # --- Plan/fact: раньше лестницы; Н/None = стоп как V2 ---
        plan = AdvSettingAutoUpdater.get_plan_data(adv)
        state: SalesStates | None = None
        fact = None
        if plan is None:
            logger.debug("[adv_id=%s] v3: no plan, skip selector", complex_adv.adv_id)
        else:
            updater = AdvSettingAutoUpdater(adv, max_last_period)
            fact = await updater.get_fact_data(ledger.keywords)

            state = detect_campaign_state(plan, fact)
            campaign_ladder_blocked = _v3_campaign_ladder_blocked(state)
            if campaign_ladder_blocked:
                logger.info(
                    "[adv_id=%s] v3: campaign state=%s — ladder wait (align V2)",
                    complex_adv.adv_id,
                    state.name if state is not None else "None",
                )

        preamble_m1_count = 0
        preamble_trim_count = 0

        if not campaign_ladder_blocked and dto is not None:
            if plan is not None and fact is not None:
                shelf_active = complex_adv.shelf_promotion_active
                shelf_click_mode = (
                    resolve_shelf_click_mode_from_adv(complex_adv)
                    if shelf_active
                    else None
                )
                aggr = normalize_v3_rollout_aggressiveness(
                    complex_adv.v3_rollout_aggressiveness
                )

                m1_actions = plan_m1_mass_cheap_promotion_with_plan_fact(
                    contexts,
                    plan=plan,
                    fact=fact,
                    shelf_promotion_active=shelf_active,
                    shelf_click_mode=shelf_click_mode,
                    aggr=aggr,
                )
                if m1_actions:
                    preamble_m1_count = len(m1_actions)
                    logger.info(
                        "[adv_id=%s] v3 preamble M1: actions=%s",
                        complex_adv.adv_id,
                        preamble_m1_count,
                    )
                    _ = ledger.apply_in_memory(m1_actions)
                    contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)

                if (
                    fact.pay_for_order is not None
                    and float(fact.pay_for_order) > float(plan.max_pay_for_order)
                ):
                    trim_click = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
                    trim_actions = plan_campaign_trim_by_max_state_cost(
                        build_prepared_from_contexts(contexts),
                        max_pay_for_order=float(plan.max_pay_for_order),
                        shelf_click_mode=trim_click,
                        aggressiveness=aggr,
                    )
                    if trim_actions:
                        preamble_trim_count = len(trim_actions)
                        logger.info(
                            "[adv_id=%s] v3 preamble trim (max=%s): actions=%s",
                            complex_adv.adv_id,
                            plan.max_pay_for_order,
                            preamble_trim_count,
                        )
                        _ = ledger.apply_in_memory(trim_actions)
                        contexts = build_keyword_v3_contexts(
                            ledger.keywords, raw_profiles
                        )

            no_data_actions = plan_no_data_activation_v3(contexts)
            if no_data_actions:
                logger.info(
                    "[adv_id=%s] v3 no_data activation planned: actions=%s",
                    complex_adv.adv_id,
                    len(no_data_actions),
                )
                _ = ledger.apply_in_memory(no_data_actions)
                contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)

        if plan is not None and not campaign_ladder_blocked:
            plan_fact_change = ChangePlanFact(adv)
            plan_fact_equal = await plan_fact_change.check_equal_in_cache(plan, fact)

            async def cache_plan_fact_snapshot() -> None:
                await plan_fact_change.set_new_plan_fact(plan, fact)

            if plan_fact_equal and state != SalesStates.OVERSPEND:
                logger.debug(
                    "[adv_id=%s] v3: plan/fact unchanged, skip selector",
                    complex_adv.adv_id,
                )
            elif dto is None:
                logger.warning(
                    "[adv_id=%s] v3: no WBAdvDTO, plan/fact cache not updated "
                    "(retry next cycle)",
                    complex_adv.adv_id,
                )
            else:
                shelf_active = complex_adv.shelf_promotion_active
                selector_actions_logged = select_v3_actions(
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
                _ = ledger.apply_in_memory(selector_actions_logged)
                await cache_plan_fact_snapshot()
                up_count = sum(
                    1 for a in selector_actions_logged if a.action.value == "UP"
                )
                down_count = sum(
                    1 for a in selector_actions_logged if a.action.value == "DOWN"
                )
                force_off_count = sum(
                    1 for a in selector_actions_logged if a.action.value == "FORCE_OFF"
                )
                m2_count = sum(
                    1 for a in selector_actions_logged if a.reason.startswith("m2_")
                )
                m3_count = sum(
                    1 for a in selector_actions_logged if a.reason.startswith("m3_")
                )
                logger.info(
                    "[adv_id=%s] v3_cycle state=%s resolve=%s fact_cpa=%s "
                    "preamble_m1=%s preamble_trim=%s "
                    "up=%s down=%s off=%s m2=%s m3=%s",
                    complex_adv.adv_id,
                    state.name,
                    compute_resolve_cost_threshold(plan, fact),
                    fact.pay_for_order,
                    preamble_m1_count,
                    preamble_trim_count,
                    up_count,
                    down_count,
                    force_off_count,
                    m2_count,
                    m3_count,
                )
                for act in selector_actions_logged:
                    sel = act.selection_log
                    if sel is not None:
                        logger.info(
                            "[adv_id=%s] v3_selection state=%s action=%s reason=%s "
                            "pool=%s pool_after_rec=%s tier=%s state_cost=%s "
                            "%s->%s move=%s imputed=%s",
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
                    [a.model_dump() for a in selector_actions_logged],
                )

        flushed = await ledger.flush_to_db(complex_adv)
        if flushed:
            logger.info(
                "[adv_id=%s] v3: netto flush committed",
                complex_adv.adv_id,
            )

        await _sync_target_places_once()
    finally:
        await _sync_target_places_once()
