"""AutoUpdater v3 orchestration (per-keyword aggression).

Порядок на **каждом** тике (``CampaignMode``):
  1. CH bid profiles; plan/fact → ``detect_campaign_state`` → ``resolve_campaign_mode``.
  2. ``NOT_READY`` — full stop (без bootstrap, realloc, selector, flush, sync).
  3. ``NO_DATA`` — campaign DATA_BOOTSTRAP → flush → target_place (force 0).
  4. ``NORMAL`` — keyword bootstrap → active invalid cleanup → [resolve valid: realloc + expansion] → MAX_CPA_GUARD
     (по ``plan.max``, вне ``is_resolve_valid``) → gate.
  5. NO_CH OFF→MIN только через ``PROFITABLE_EXPANSION`` (V2 CPO ≤ resolve).
  6. Нетто-flush + ``target_place`` только если режим не ``NOT_READY``.

Наблюдаемость: ``v3_selection`` и ``docks/V3_UPDATER_VALIDATION.md``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_eligibility_map,
    build_target_place_fallback_zero_by_keyword_id,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    plan_campaign_no_data_bootstrap_safe,
    plan_data_bootstrap_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    cache_worst_costs_for_adv,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    compute_resolve_cost_threshold,
    is_resolve_valid,
    plan_active_invalid_state_cleanup,
    plan_cost_reallocation,
    plan_max_cpa_guard,
    plan_profitable_expansion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    select_v3_post_gate_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync import (
    sync_keyword_target_places_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
    allows_ladder_phases,
    is_campaign_full_stop,
    resolve_campaign_mode,
)
from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
    TrafficClicksManager,
)
from app.modules.shop_runner.service_manager.coroutine_phase_trace import (
    AdvPhaseTrace,
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

# ``get_wb_advs_dto`` → ``PlanFactProvider`` использует тот же default last_days.
_WB_ADV_DTO_FACT_LAST_DAYS = 2

# TODO: централизовать получение план-факта
async def _resolve_v3_fact_data(
    *,
    dto: WBAdvDTO | None,
    updater: AdvSettingAutoUpdater,
    keywords: list[CalculatedKeyword],
    max_last_period: int,
) -> tuple[FactData, str]:
    """Fact для V3 ladder без повторного ``get_stat_data``, если fact уже в ``WBAdvDTO``.

    ``get_wb_advs_dto`` собирает fact в ``_collect_adv_data_parts`` (CH). Повторный
    ``AdvSettingAutoUpdater.get_fact_data`` на том же тике — дубль запроса в ClickHouse.

    Returns:
        (fact, source) — source ``\"dto\"`` или ``\"updater\"`` для диагностики.
    """
    if (
        dto is not None
        and isinstance(dto, WBAdvDTO)
        and max_last_period == _WB_ADV_DTO_FACT_LAST_DAYS
    ):
        return dto.fact, "dto"
    return await updater.get_fact_data(keywords), "updater"
#

def _apply_v3_phase(
    ledger: V3TickKeywordLedger,
    actions: list[V3Action],
    raw_profiles: dict[str, list[BidPosition]],
) -> list[KeywordV3Context]:
    """Применить фазу in-memory и пересобрать контексты."""
    if actions:
        ledger.apply_in_memory(actions)
    return build_keyword_v3_contexts(ledger.keywords, raw_profiles)


async def _load_v3_wb_context(
    complex_adv: ComplexAdv,
    *,
    wb_shop_data_manager: WBShopDataManager,
    dbg_phase: Callable[[str, dict[str, object] | None], None] | None = None,
) -> tuple[WBAdvDTO | None, dict[str, list[BidPosition]]]:
    """Один запрос WBAdvDTO + bid profiles на цикл V3 (CH)."""
    def _step(name: str, extra: dict[str, object] | None = None) -> None:
        if dbg_phase is not None:
            dbg_phase(name, extra)

    shelf_active = complex_adv.shelf_promotion_active
    if shelf_active:
        await TrafficClicksManager().enrich(complex_adv)
        _step("traffic_enrich_done", {"shelf_active": True})
    else:
        _step("traffic_enrich_skipped", {"shelf_active": False})

    _step("before_get_wb_advs_dto")
    wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
    _step("get_wb_advs_dto", {"dto_count": len(wb_dtos)})
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
        backfill_ok = await wb_shop_data_manager.backfill_min_bids_for_adv(complex_adv)
        _step("min_bids_backfill", {"ok": backfill_ok, "nmid": nmid})
        if backfill_ok:
            wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
            if wb_dtos:
                dto = wb_dtos[0]
        else:
            logger.error(
                "[adv_id=%s] v3: min_bid backfill failed for nmid=%s",
                complex_adv.adv_id,
                nmid,
            )
    else:
        _step("min_bids_cache_hit", {"nmid": nmid})

    predictor = build_predict_keywords_target_place()
    raw_profiles = await predictor.get_keyword_bid_profiles(
        dto, dto.min_target_position
    )
    _step(
        "get_keyword_bid_profiles",
        {"profiles_count": len(raw_profiles), "min_target_position": dto.min_target_position},
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
    force_all_target_place_zero: bool = False,
    target_place_fallback_zero_by_keyword_id: dict[int, bool] | None = None,
) -> None:
    """Best-effort sync ``target_place`` без подмены ошибки из ``try`` (PEP 409)."""
    try:
        await sync_keyword_target_places_v3(
            dto,
            raw_profiles,
            calculated_by_text=_calculated_keywords_by_text(keywords),
            force_all_target_place_zero=force_all_target_place_zero,
            target_place_fallback_zero_by_keyword_id=(
                target_place_fallback_zero_by_keyword_id
            ),
        )
    except Exception: # type: ignore
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
    trace = AdvPhaseTrace(
        coroutine="process_adv_v3",
        shop_id=complex_adv.shop_id,
        adv_id=complex_adv.adv_id,
    )
    adv = complex_adv.adv_setting
    with trace.phase("get_keywords"):
        keywords = await complex_adv.get_keywords()
    trace.marker("keywords_loaded", extra={"keywords_count": len(keywords)})
    ledger = V3TickKeywordLedger.from_keywords(keywords)

    with trace.phase("load_v3_wb_context"):
        dto, raw_profiles = await _load_v3_wb_context(
            complex_adv,
            wb_shop_data_manager=wb_shop_data_manager,
            dbg_phase=trace.dbg_phase,
        )
    target_place_synced = False
    campaign_mode = CampaignMode.NOT_READY
    sync_force_zero = False
    sync_fallback_by_id: dict[int, bool] | None = None
    ladder_inputs: LadderInputs | None = None
    policy: SelectionPolicy | None = None
    campaign_orders_per_cart_7d: float | None = None

    async def _sync_target_places_once() -> None:
        """После flush; в finally — если тик оборвался раньше."""
        nonlocal target_place_synced
        if target_place_synced or is_campaign_full_stop(campaign_mode):
            return
        if dto is not None and complex_adv.individual_keywords_target_place_mode:
            with trace.phase("sync_keyword_target_places_v3"):
                await _safe_sync_target_places_v3(
                    complex_adv,
                    dto,
                    raw_profiles,
                    keywords=ledger.keywords,
                    force_all_target_place_zero=sync_force_zero,
                    target_place_fallback_zero_by_keyword_id=sync_fallback_by_id,
                )
            target_place_synced = True

    preamble_bootstrap_count = 0
    preamble_cleanup_count = 0
    preamble_realloc_count = 0
    preamble_expansion_count = 0
    preamble_guard_count = 0

    try:
        with trace.phase("build_keyword_v3_contexts"):
            contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)
        with trace.phase("get_plan_data"):
            plan = AdvSettingAutoUpdater.get_plan_data(adv)
        state: SalesStates | None = None
        fact = None
        if plan is None:
            logger.debug("[adv_id=%s] v3: no plan, skip ladder", complex_adv.adv_id)
        else:
            with trace.phase("resolve_fact_data"):
                updater = AdvSettingAutoUpdater(adv, max_last_period)
                fact, fact_source = await _resolve_v3_fact_data(
                    dto=dto,
                    updater=updater,
                    keywords=ledger.keywords,
                    max_last_period=max_last_period,
                )
            with trace.phase("detect_campaign_state"):
                state = detect_campaign_state(plan, fact)
                campaign_mode = resolve_campaign_mode(state)
            logger.info(
                "[adv_id=%s] v3: campaign_mode=%s state=%s fact_source=%s",
                complex_adv.adv_id,
                campaign_mode.value,
                state.name if state is not None else "None",
                fact_source,
            )
        if is_campaign_full_stop(campaign_mode):
            logger.info(
                "[adv_id=%s] v3 NOT_READY: full stop (no bootstrap, flush, sync)",
                complex_adv.adv_id,
            )
            return

        if dto is not None and plan is not None:
            from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
                load_campaign_orders_per_cart_7d,
            )

            with trace.phase("load_campaign_orders_per_cart_7d"):
                campaign_orders_per_cart_7d = await load_campaign_orders_per_cart_7d(
                    adv
                )

        # Взаимоисключающий campaign preamble (см. docks/V3_UPDATER_VALIDATION.md):
        # NO_DATA  → только plan_campaign_no_data_bootstrap_safe + sync_force_zero
        # NORMAL   → plan_data_bootstrap_v3 + realloc / expansion / guard
        if campaign_mode == CampaignMode.NO_DATA and dto is not None:
            with trace.phase("preamble_no_data_bootstrap"):
                bootstrap_actions = plan_campaign_no_data_bootstrap_safe(contexts)
            if bootstrap_actions:
                preamble_bootstrap_count += len(bootstrap_actions)
                logger.info(
                    "[adv_id=%s] v3 DATA_BOOTSTRAP (NO_DATA): actions=%s",
                    complex_adv.adv_id,
                    len(bootstrap_actions),
                )
                contexts = _apply_v3_phase(
                    ledger,
                    bootstrap_actions,
                    raw_profiles,
                )
            sync_force_zero = True

        elif campaign_mode == CampaignMode.NORMAL and dto is not None:
            assert plan is not None and fact is not None
            # NORMAL-only: не вызывать для NO_DATA / NOT_READY
            with trace.phase("preamble_keyword_bootstrap"):
                keyword_bootstrap_actions = plan_data_bootstrap_v3(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                )
            if keyword_bootstrap_actions:
                preamble_bootstrap_count += len(keyword_bootstrap_actions)
                logger.info(
                    "[adv_id=%s] v3 KEYWORD_BOOTSTRAP: actions=%s",
                    complex_adv.adv_id,
                    len(keyword_bootstrap_actions),
                )
                contexts = _apply_v3_phase(
                    ledger,
                    keyword_bootstrap_actions,
                    raw_profiles,
                )

            shelf_active = complex_adv.shelf_promotion_active
            shelf_click_mode = (
                resolve_shelf_click_mode_from_adv(complex_adv)
                if shelf_active
                else None
            )
            aggr = normalize_v3_rollout_aggressiveness(
                complex_adv.v3_rollout_aggressiveness
            )
            click_mode = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
            policy = SelectionPolicy.from_aggressiveness(
                click_mode=click_mode,
                aggressiveness=aggr,
            )
            resolve = compute_resolve_cost_threshold(plan, fact)
            from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
                load_rec_orders_per_view_for_v3,
            )

            with trace.phase("load_rec_orders_per_view_for_v3"):
                rec_orders_per_view = await load_rec_orders_per_view_for_v3(
                    adv,
                    rec_system_promotion_mode_active=complex_adv.rec_system_promotion_mode_active,
                )
            with trace.phase("preamble_build_ladder_inputs"):
                ladder_inputs = LadderInputs.from_contexts(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                    rec_orders_per_view=rec_orders_per_view,
                )
            with trace.phase("preamble_cache_worst_costs"):
                await cache_worst_costs_for_adv(
                    complex_adv.adv_id, ladder_inputs.worst_costs
                )
            with trace.phase("preamble_build_eligibility"):
                eligibility = build_eligibility_map(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                )
            with trace.phase("preamble_build_prepared"):
                prepared = build_prepared_from_contexts(contexts)
            cleanup_resolve = resolve if is_resolve_valid(plan, resolve) else None
            with trace.phase("preamble_active_invalid_cleanup"):
                cleanup_actions = plan_active_invalid_state_cleanup(
                    prepared,
                    max_pay_for_order=float(plan.max_pay_for_order),
                    resolve=cleanup_resolve,
                    eligibility_by_ks_id=eligibility,
                    ladder_inputs=ladder_inputs,
                )
            if cleanup_actions:
                preamble_cleanup_count = len(cleanup_actions)
                logger.info(
                    "[adv_id=%s] v3 ACTIVE_INVALID_CLEANUP: actions=%s",
                    complex_adv.adv_id,
                    preamble_cleanup_count,
                )
                contexts = _apply_v3_phase(
                    ledger,
                    cleanup_actions,
                    raw_profiles,
                )
                eligibility = build_eligibility_map(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                )
                prepared = build_prepared_from_contexts(contexts)
                ladder_inputs = LadderInputs.from_contexts(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                    rec_orders_per_view=rec_orders_per_view,
                )
                await cache_worst_costs_for_adv(
                    complex_adv.adv_id, ladder_inputs.worst_costs
                )

            if is_resolve_valid(plan, resolve):
                # COST_REALLOCATION — portfolio DOWN при запасе по CPA (не overspend guard):
                # снимаем дорогую агрессию, затем PROFITABLE_EXPANSION перераспределяет
                # в более дешёвые passing states. При высоком fact CPA — MAX_CPA_GUARD ниже.
                if (
                    fact.pay_for_order is not None
                    and float(fact.pay_for_order) < 0.9 * float(resolve)
                ):
                    with trace.phase("preamble_cost_reallocation"):
                        realloc_actions = plan_cost_reallocation(
                            prepared,
                            resolve=resolve,
                            policy=policy,
                            eligibility_by_ks_id=eligibility,
                            ladder_inputs=ladder_inputs,
                        )
                    if realloc_actions:
                        preamble_realloc_count = len(realloc_actions)
                        logger.info(
                            "[adv_id=%s] v3 COST_REALLOCATION: actions=%s",
                            complex_adv.adv_id,
                            preamble_realloc_count,
                        )
                        contexts = _apply_v3_phase(
                            ledger,
                            realloc_actions,
                            raw_profiles,
                        )
                        eligibility = build_eligibility_map(
                            contexts,
                            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                        )
                        prepared = build_prepared_from_contexts(contexts)
                        ladder_inputs = LadderInputs.from_contexts(
                            contexts,
                            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                            rec_orders_per_view=rec_orders_per_view,
                        )
                        await cache_worst_costs_for_adv(
                            complex_adv.adv_id, ladder_inputs.worst_costs
                        )

                with trace.phase("preamble_profitable_expansion"):
                    expansion_actions = plan_profitable_expansion(
                        prepared,
                        resolve=resolve,
                        policy=policy,
                        eligibility_by_ks_id=eligibility,
                        ladder_inputs=ladder_inputs,
                    )
                if expansion_actions:
                    preamble_expansion_count = len(expansion_actions)
                    logger.info(
                        "[adv_id=%s] v3 PROFITABLE_EXPANSION: actions=%s",
                        complex_adv.adv_id,
                        preamble_expansion_count,
                    )
                    contexts = _apply_v3_phase(
                        ledger,
                        expansion_actions,
                        raw_profiles,
                    )

            guard_condition = (
                fact.pay_for_order is not None
                and float(fact.pay_for_order) > float(plan.max_pay_for_order)
            )
            if guard_condition:
                guard_eligibility = build_eligibility_map(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                )
                guard_prepared = build_prepared_from_contexts(contexts)
                guard_ladder_inputs = LadderInputs.from_contexts(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                    rec_orders_per_view=rec_orders_per_view,
                )
                await cache_worst_costs_for_adv(
                    complex_adv.adv_id, guard_ladder_inputs.worst_costs
                )
                with trace.phase("preamble_max_cpa_guard"):
                    guard_actions = plan_max_cpa_guard(
                        guard_prepared,
                        max_pay_for_order=float(plan.max_pay_for_order),
                        shelf_click_mode=click_mode,
                        aggressiveness=aggr,
                        eligibility_by_ks_id=guard_eligibility,
                        ladder_inputs=guard_ladder_inputs,
                    )
                if guard_actions:
                    preamble_guard_count = len(guard_actions)
                    logger.info(
                        "[adv_id=%s] v3 MAX_CPA_GUARD: actions=%s",
                        complex_adv.adv_id,
                        preamble_guard_count,
                    )
                    contexts = _apply_v3_phase(
                        ledger,
                        guard_actions,
                        raw_profiles,
                    )

            # Всегда перед sync: даже если bootstrap/cleanup/expansion/guard без actions.
            with trace.phase("preamble_build_sync_fallback"):
                sync_fallback_by_id = build_target_place_fallback_zero_by_keyword_id(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                )

        if plan is not None and allows_ladder_phases(campaign_mode):
            with trace.phase("plan_fact_cache_check"):
                plan_fact_change = ChangePlanFact(adv)
                plan_fact_equal = await plan_fact_change.check_equal_in_cache(
                    plan, fact
                )

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
                with trace.phase("select_post_gate_actions"):
                    shelf_active = complex_adv.shelf_promotion_active
                    selector_actions_logged = select_v3_post_gate_actions(
                        contexts=contexts,
                        shelf_promotion_active=shelf_active,
                        shelf_click_mode=resolve_shelf_click_mode_from_adv(complex_adv)
                        if shelf_active
                        else None,
                        ladder_inputs=ladder_inputs,
                        policy=policy,
                    )
                with trace.phase("apply_selector_actions"):
                    _ = ledger.apply_in_memory(selector_actions_logged)
                with trace.phase("cache_plan_fact_snapshot"):
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
                logger.info(
                    "[adv_id=%s] v3_cycle state=%s resolve=%s fact_cpa=%s "
                    "bootstrap=%s cleanup=%s realloc=%s expansion=%s guard=%s "
                    "post_gate up=%s down=%s off=%s",
                    complex_adv.adv_id,
                    state.name if state else "None",
                    compute_resolve_cost_threshold(plan, fact)
                    if fact is not None
                    else None,
                    fact.pay_for_order if fact else None,
                    preamble_bootstrap_count,
                    preamble_cleanup_count,
                    preamble_realloc_count,
                    preamble_expansion_count,
                    preamble_guard_count,
                    up_count,
                    down_count,
                    force_off_count,
                )

        if not is_campaign_full_stop(campaign_mode):
            with trace.phase("flush_to_db"):
                flushed_to_db = await ledger.flush_to_db(complex_adv)
            if flushed_to_db:
                logger.info(
                    "[adv_id=%s] v3: netto flush committed",
                    complex_adv.adv_id,
                )
            with trace.phase("sync_target_places_once"):
                await _sync_target_places_once()
    finally:
        if not is_campaign_full_stop(campaign_mode):
            with trace.phase("sync_target_places_once_finally"):
                await _sync_target_places_once()
