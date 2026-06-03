"""AutoUpdater v3 orchestration (per-keyword aggression).

Порядок на **каждом** тике (``CampaignMode``):
  1. CH bid profiles; plan/fact → ``detect_campaign_state`` → ``resolve_campaign_mode``.
  2. ``NOT_READY`` — full stop (без bootstrap, realloc, selector, flush, sync).
  3. ``NO_DATA`` — campaign DATA_BOOTSTRAP → flush → target_place (force 0).
  4. ``NORMAL`` — preamble **filter → sync → B → U → S → G → R → enable → calibration(TIGHTEN|LOOSEN)** → post-gate → snapshot.

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache import (
    ChangePlanFactViews,
    resolve_complex_adv_total_views,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
    CalibrationStepState,
    classify_calibration_direct,
    resolve_effective_calibration_steps,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_state_cache import (
    V3CalibrationStepState,
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
    KeywordV3Eligibility,
    build_eligibility_map,
    build_target_place_fallback_zero_by_keyword_id,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    plan_campaign_no_data_bootstrap_safe,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    filter_operable_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3TickReportCollector,
    find_white_list_cost_leader,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_phase_notes import (
    summarize_phase_zero_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_redis import (
    persist_v3_tick_report,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_preamble_phases import (
    plan_max_cpa_guard_phase,
    plan_mode_cap_down,
    plan_passing_up,
    plan_pay_for_order_gap_enable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    compute_resolve_cost_threshold,
    is_resolve_valid,
    plan_cost_reallocation,
    plan_resolve_calibration,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
    build_prepared_from_contexts,
    plan_shelf_rec_false_cleanup_down,
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


def _phase_outcome_note_if_empty(
    phase_id: str,
    actions: list[V3Action],
    *,
    prepared: PreparedList,
    **kwargs: object,
) -> str | None:
    """Русская причина нулевого исхода фазы; ``None`` если есть действия."""
    if actions:
        return None
    return summarize_phase_zero_actions(phase_id, prepared=prepared, **kwargs)

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

def _apply_v3_phase(
    ledger: V3TickKeywordLedger,
    actions: list[V3Action],
    raw_profiles: dict[str, list[BidPosition]],
) -> list[KeywordV3Context]:
    """Применить фазу in-memory и пересобрать контексты (все ключи)."""
    if actions:
        ledger.apply_in_memory(actions)
    return build_keyword_v3_contexts(ledger.keywords, raw_profiles)


def _apply_v3_phase_operable(
    ledger: V3TickKeywordLedger,
    actions: list[V3Action],
    raw_profiles: dict[str, list[BidPosition]],
) -> tuple[list[KeywordV3Context], list[KeywordV3Context]]:
    """Применить фазу; вернуть (operable_contexts, all_contexts)."""
    all_contexts = _apply_v3_phase(ledger, actions, raw_profiles)
    return filter_operable_v3_contexts(all_contexts), all_contexts


def _prepare_v3_operable_ladder_contexts(
    ledger: V3TickKeywordLedger,
    raw_profiles: dict[str, list[BidPosition]],
    all_contexts: list[KeywordV3Context],
) -> tuple[list[KeywordV3Context], list[KeywordV3Context], int]:
    """Filter operable (1|2) → sync hard_status ↔ mode → rebuild.

    Returns:
        (operable_contexts, all_contexts, sync_fixed_count)
    """
    _ = filter_operable_v3_contexts(all_contexts)
    sync_fixed = ledger.sync_operable_hard_status_with_strategy_mode()
    all_contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)
    operable_contexts = filter_operable_v3_contexts(all_contexts)
    return operable_contexts, all_contexts, sync_fixed


def _refresh_v3_tick_state(
    contexts: list[KeywordV3Context],
    *,
    campaign_orders_per_cart_7d: float | None,
    rec_orders_per_view: float | None,
) -> tuple[
    "PreparedList",
    dict[int, "KeywordV3Eligibility"],
    LadderInputs,
]:
    """Пересобрать prepared, eligibility и ladder_inputs после preamble-фазы."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        PreparedList,
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
    return prepared, eligibility, ladder_inputs


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
    tick_report = V3TickReportCollector()
    tick_report.set_aggression_before(ledger.keywords)
    tick_report_ready = False

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

    preamble_cap_down_count = 0
    preamble_passing_up_count = 0
    preamble_shelf_count = 0
    preamble_realloc_count = 0
    preamble_enable_count = 0
    preamble_calibration_count = 0
    calibration_executed_this_tick = False
    preamble_guard_count = 0
    preamble_hard_status_sync_count = 0
    plan_fact_change: ChangePlanFact | None = None
    views_cache: ChangePlanFactViews | None = None
    plan_fact_equal = False
    views_equal = False
    current_views: int | None = None
    calibration_step_cache: V3CalibrationStepState | None = None
    effective_calibration_steps = 1
    current_calibration_direct: CalibrationDirect | None = None
    calibration_prev_effective_steps: int | None = None
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None
    ladder_inputs: LadderInputs | None = None

    try:
        with trace.phase("build_keyword_v3_contexts"):
            all_contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)
            contexts = all_contexts
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
            # Ранний fallback: finally/sync при исключении в preamble до финальной пересборки.
            with trace.phase("preamble_build_sync_fallback_early"):
                sync_fallback_by_id = build_target_place_fallback_zero_by_keyword_id(
                    all_contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                )

        if (
            dto is not None
            and plan is not None
            and campaign_mode in (CampaignMode.NO_DATA, CampaignMode.NORMAL)
        ):
            with trace.phase("preamble_filter_operable"):
                operable_before = len(filter_operable_v3_contexts(all_contexts))
                trace.marker(
                    "operable_filtered",
                    extra={
                        "total_contexts": len(all_contexts),
                        "operable_contexts": operable_before,
                    },
                )
            with trace.phase("preamble_hard_status_mode_sync"):
                contexts, all_contexts, preamble_hard_status_sync_count = (
                    _prepare_v3_operable_ladder_contexts(
                        ledger,
                        raw_profiles,
                        all_contexts,
                    )
                )
                if preamble_hard_status_sync_count:
                    logger.info(
                        "[adv_id=%s] v3 HARD_STATUS_MODE_SYNC: fixed=%s",
                        complex_adv.adv_id,
                        preamble_hard_status_sync_count,
                    )
            tick_report.record_filter(
                total=len(all_contexts),
                operable=operable_before,
            )
            tick_report.record_sync(preamble_hard_status_sync_count)
            tick_report_ready = True

        # Взаимоисключающий campaign preamble (см. docks/V3_UPDATER_VALIDATION.md):
        # NO_DATA  → filter/sync → plan_campaign_no_data_bootstrap_safe + sync_force_zero
        # NORMAL   → filter/sync → B → U → S → G → R → enable → calibration(TIGHTEN|LOOSEN)
        preamble_no_data_bootstrap_count = 0
        if campaign_mode == CampaignMode.NO_DATA and dto is not None:
            with trace.phase("preamble_no_data_bootstrap"):
                bootstrap_actions = plan_campaign_no_data_bootstrap_safe(contexts)
            tick_report.record_phase(
                "no_data_bootstrap",
                bootstrap_actions,
                outcome_note=_phase_outcome_note_if_empty(
                    "no_data_bootstrap",
                    bootstrap_actions,
                    prepared=[],
                ),
            )
            if bootstrap_actions:
                preamble_no_data_bootstrap_count = len(bootstrap_actions)
                logger.info(
                    "[adv_id=%s] v3 DATA_BOOTSTRAP (NO_DATA): actions=%s",
                    complex_adv.adv_id,
                    preamble_no_data_bootstrap_count,
                )
                contexts, all_contexts = _apply_v3_phase_operable(
                    ledger,
                    bootstrap_actions,
                    raw_profiles,
                )
            sync_force_zero = True

        elif campaign_mode == CampaignMode.NORMAL and dto is not None:
            assert plan is not None and fact is not None
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
            plan_fact_change = ChangePlanFact(adv)
            with trace.phase("plan_fact_cache_check"):
                plan_fact_equal = await plan_fact_change.check_equal_in_cache(
                    plan, fact
                )
            views_cache = ChangePlanFactViews(adv)
            with trace.phase("calibration_views_resolve"):
                try:
                    current_views = await resolve_complex_adv_total_views(
                        complex_adv,
                        max_last_period=max_last_period,
                    )
                    cached_views = await views_cache.get_cached_views()
                    views_equal = (
                        cached_views is not None and cached_views == current_views
                    )
                except Exception:
                    logger.warning(
                        "[adv_id=%s] v3: views resolve failed, "
                        "calibration views gate fail-closed",
                        complex_adv.adv_id,
                        exc_info=True,
                    )
                    views_equal = True
                    current_views = None
            calibration_step_cache = V3CalibrationStepState(adv)
            current_calibration_direct = classify_calibration_direct(
                fact.pay_for_order,
                resolve,
            )
            with trace.phase("calibration_effective_steps_resolve"):
                calibration_prev_state = await calibration_step_cache.get_state()
                calibration_prev_effective_steps = (
                    calibration_prev_state.effective_steps
                    if calibration_prev_state is not None
                    else None
                )
                effective_calibration_steps = resolve_effective_calibration_steps(
                    complex_adv.keyword_calibration_max_step,
                    prev=calibration_prev_state,
                    current_direct=current_calibration_direct,
                )
                logger.debug(
                    "[adv_id=%s] v3 calibration steps: effective=%s base_max=%s "
                    "direct=%s prev_direct=%s",
                    complex_adv.adv_id,
                    effective_calibration_steps,
                    complex_adv.keyword_calibration_max_step,
                    current_calibration_direct.value,
                    calibration_prev_state.direct.value
                    if calibration_prev_state is not None
                    else None,
                )
            from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
                load_rec_orders_per_view_for_v3,
            )

            with trace.phase("load_rec_orders_per_view_for_v3"):
                rec_orders_per_view = await load_rec_orders_per_view_for_v3(
                    adv,
                    rec_system_promotion_mode_active=complex_adv.rec_system_promotion_mode_active,
                )
            prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                contexts,
                campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                rec_orders_per_view=rec_orders_per_view,
            )
            guard_applied = False

            with trace.phase("preamble_mode_cap_down"):
                cap_actions = plan_mode_cap_down(
                    prepared,
                    eligibility_by_ks_id=eligibility,
                )
            tick_report.record_phase(
                "cap_down",
                cap_actions,
                outcome_note=_phase_outcome_note_if_empty(
                    "cap_down",
                    cap_actions,
                    prepared=prepared,
                    eligibility_by_ks_id=eligibility,
                ),
            )
            if cap_actions:
                preamble_cap_down_count = len(cap_actions)
                logger.info(
                    "[adv_id=%s] v3 MODE_CAP_DOWN: actions=%s",
                    complex_adv.adv_id,
                    preamble_cap_down_count,
                )
                contexts, all_contexts = _apply_v3_phase_operable(
                    ledger, cap_actions, raw_profiles
                )
                prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                    contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                    rec_orders_per_view=rec_orders_per_view,
                )

            if is_resolve_valid(plan, resolve):
                with trace.phase("preamble_passing_up"):
                    passing_up_actions = plan_passing_up(
                        prepared,
                        resolve=resolve,
                        policy=policy,
                        eligibility_by_ks_id=eligibility,
                        ladder_inputs=ladder_inputs,
                    )
                tick_report.record_phase(
                    "passing_up",
                    passing_up_actions,
                    outcome_note=_phase_outcome_note_if_empty(
                        "passing_up",
                        passing_up_actions,
                        prepared=prepared,
                        resolve=resolve,
                        policy=policy,
                        eligibility_by_ks_id=eligibility,
                        ladder_inputs=ladder_inputs,
                    ),
                )
                if passing_up_actions:
                    preamble_passing_up_count = len(passing_up_actions)
                    logger.info(
                        "[adv_id=%s] v3 PASSING_UP: actions=%s",
                        complex_adv.adv_id,
                        preamble_passing_up_count,
                    )
                    contexts, all_contexts = _apply_v3_phase_operable(
                        ledger, passing_up_actions, raw_profiles
                    )
                    prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                        contexts,
                        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                        rec_orders_per_view=rec_orders_per_view,
                    )
            else:
                tick_report.record_phase(
                    "passing_up",
                    skip_reason="resolve_invalid",
                )

            if shelf_active:
                with trace.phase("preamble_shelf_rec_cleanup"):
                    shelf_actions = plan_shelf_rec_false_cleanup_down(
                        prepared,
                        click_mode=click_mode,
                        ladder_inputs=ladder_inputs,
                        policy=policy,
                    )
                tick_report.record_phase(
                    "shelf_cleanup",
                    shelf_actions,
                    extra={"shelf_active": True},
                    outcome_note=_phase_outcome_note_if_empty(
                        "shelf_cleanup",
                        shelf_actions,
                        prepared=prepared,
                        shelf_active=True,
                        shelf_click_mode=click_mode,
                        ladder_inputs=ladder_inputs,
                    ),
                )
                if shelf_actions:
                    preamble_shelf_count = len(shelf_actions)
                    logger.info(
                        "[adv_id=%s] v3 SHELF_REC_CLEANUP: actions=%s",
                        complex_adv.adv_id,
                        preamble_shelf_count,
                    )
                    contexts, all_contexts = _apply_v3_phase_operable(
                        ledger, shelf_actions, raw_profiles
                    )
                    prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                        contexts,
                        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                        rec_orders_per_view=rec_orders_per_view,
                    )
            else:
                tick_report.record_phase(
                    "shelf_cleanup",
                    skip_reason="shelf_inactive",
                )

            guard_condition = (
                fact.pay_for_order is not None
                and float(fact.pay_for_order) > float(plan.max_pay_for_order)
            )
            if guard_condition:
                with trace.phase("preamble_max_cpa_guard"):
                    guard_actions = plan_max_cpa_guard_phase(
                        prepared,
                        max_pay_for_order=float(plan.max_pay_for_order),
                        shelf_click_mode=click_mode,
                        aggressiveness=aggr,
                        eligibility_by_ks_id=eligibility,
                        ladder_inputs=ladder_inputs,
                    )
                tick_report.record_phase(
                    "max_cpa_guard",
                    guard_actions,
                    outcome_note=_phase_outcome_note_if_empty(
                        "max_cpa_guard",
                        guard_actions,
                        prepared=prepared,
                        max_pay_for_order=float(plan.max_pay_for_order),
                        shelf_click_mode=click_mode,
                        aggressiveness=aggr,
                        eligibility_by_ks_id=eligibility,
                        ladder_inputs=ladder_inputs,
                    ),
                )
                if guard_actions:
                    guard_applied = True
                    preamble_guard_count = len(guard_actions)
                    logger.info(
                        "[adv_id=%s] v3 MAX_CPA_GUARD: actions=%s",
                        complex_adv.adv_id,
                        preamble_guard_count,
                    )
                    contexts, all_contexts = _apply_v3_phase_operable(
                        ledger, guard_actions, raw_profiles
                    )
                    prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                        contexts,
                        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                        rec_orders_per_view=rec_orders_per_view,
                    )
            else:
                tick_report.record_phase(
                    "max_cpa_guard",
                    skip_reason="fact_le_max",
                )

            if is_resolve_valid(plan, resolve):
                with trace.phase("preamble_cost_reallocation"):
                    realloc_actions = plan_cost_reallocation(
                        prepared,
                        resolve=resolve,
                        policy=policy,
                        eligibility_by_ks_id=eligibility,
                        ladder_inputs=ladder_inputs,
                    )
                tick_report.record_phase(
                    "cost_reallocation",
                    realloc_actions,
                    outcome_note=_phase_outcome_note_if_empty(
                        "cost_reallocation",
                        realloc_actions,
                        prepared=prepared,
                        resolve=resolve,
                        policy=policy,
                    ),
                )
                if realloc_actions:
                    preamble_realloc_count = len(realloc_actions)
                    logger.info(
                        "[adv_id=%s] v3 COST_REALLOCATION: actions=%s",
                        complex_adv.adv_id,
                        preamble_realloc_count,
                    )
                    contexts, all_contexts = _apply_v3_phase_operable(
                        ledger, realloc_actions, raw_profiles
                    )
                    prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                        contexts,
                        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                        rec_orders_per_view=rec_orders_per_view,
                    )

                with trace.phase("preamble_pay_for_order_gap_enable"):
                    enable_actions = plan_pay_for_order_gap_enable(
                        prepared,
                        eligibility_by_ks_id=eligibility,
                        fact_pay_for_order=(
                            float(fact.pay_for_order)
                            if fact.pay_for_order is not None
                            else None
                        ),
                        resolve=float(resolve),
                        plan_fact_changed=not plan_fact_equal,
                        views_changed=not views_equal,
                    )
                tick_report.record_phase(
                    "pay_for_order_gap_enable",
                    enable_actions,
                    outcome_note=_phase_outcome_note_if_empty(
                        "pay_for_order_gap_enable",
                        enable_actions,
                        prepared=prepared,
                        eligibility_by_ks_id=eligibility,
                        fact_pay_for_order=(
                            float(fact.pay_for_order)
                            if fact.pay_for_order is not None
                            else None
                        ),
                        resolve=float(resolve),
                        plan_fact_changed=not plan_fact_equal,
                        views_changed=not views_equal,
                    ),
                )
                if enable_actions:
                    preamble_enable_count = len(enable_actions)
                    logger.info(
                        "[adv_id=%s] v3 PAY_FOR_ORDER_GAP_ENABLE: actions=%s",
                        complex_adv.adv_id,
                        preamble_enable_count,
                    )
                    contexts, all_contexts = _apply_v3_phase_operable(
                        ledger, enable_actions, raw_profiles
                    )
                    prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                        contexts,
                        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                        rec_orders_per_view=rec_orders_per_view,
                    )

                calibration_in_range = (
                    fact.pay_for_order is not None
                    and float(fact.pay_for_order)
                    <= float(plan.max_pay_for_order)
                )
                calibration_condition = (
                    not guard_applied
                    and not plan_fact_equal
                    and not views_equal
                    and calibration_in_range
                    and current_calibration_direct is not None
                )
                if calibration_condition:
                    calibration_executed_this_tick = True
                    with trace.phase("preamble_resolve_calibration"):
                        calibration_actions = plan_resolve_calibration(
                            prepared,
                            resolve=float(resolve),
                            calibration_direct=current_calibration_direct,
                            shelf_click_mode=click_mode,
                            aggressiveness=aggr,
                            eligibility_by_ks_id=eligibility,
                            ladder_inputs=ladder_inputs,
                            max_effective_steps=effective_calibration_steps,
                        )
                    tick_report.record_phase(
                        "resolve_calibration",
                        calibration_actions,
                        extra={
                            "calibration_direct": current_calibration_direct.value,
                            "effective_steps": effective_calibration_steps,
                        },
                        outcome_note=_phase_outcome_note_if_empty(
                            "resolve_calibration",
                            calibration_actions,
                            prepared=prepared,
                            resolve=float(resolve),
                            calibration_direct=current_calibration_direct,
                            shelf_click_mode=click_mode,
                            aggressiveness=aggr,
                            eligibility_by_ks_id=eligibility,
                            ladder_inputs=ladder_inputs,
                            max_effective_steps=effective_calibration_steps,
                        ),
                    )
                    if calibration_actions:
                        preamble_calibration_count = len(calibration_actions)
                        logger.info(
                            "[adv_id=%s] v3 RESOLVE_CALIBRATION (%s): actions=%s",
                            complex_adv.adv_id,
                            current_calibration_direct.value,
                            preamble_calibration_count,
                        )
                        contexts, all_contexts = _apply_v3_phase_operable(
                            ledger, calibration_actions, raw_profiles
                        )
                        prepared, eligibility, ladder_inputs = _refresh_v3_tick_state(
                            contexts,
                            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                            rec_orders_per_view=rec_orders_per_view,
                        )
                elif calibration_in_range and guard_applied:
                    tick_report.record_phase(
                        "resolve_calibration",
                        skip_reason="guard_applied",
                    )
                    logger.debug(
                        "[adv_id=%s] v3 RESOLVE_CALIBRATION skipped: guard_applied",
                        complex_adv.adv_id,
                    )
                elif calibration_in_range:
                    cal_skip_reason = (
                        "plan_fact_unchanged_and_views_unchanged"
                        if plan_fact_equal and views_equal
                        else "plan_fact_unchanged"
                        if plan_fact_equal
                        else "views_unchanged"
                    )
                    tick_report.record_phase(
                        "resolve_calibration",
                        skip_reason=cal_skip_reason,
                    )
                    logger.debug(
                        "[adv_id=%s] v3 RESOLVE_CALIBRATION skipped: %s",
                        complex_adv.adv_id,
                        cal_skip_reason,
                    )
                else:
                    tick_report.record_phase(
                        "resolve_calibration",
                        skip_reason="fact_gt_max",
                    )
            else:
                tick_report.record_phase(
                    "cost_reallocation",
                    skip_reason="resolve_invalid",
                )
                tick_report.record_phase(
                    "pay_for_order_gap_enable",
                    skip_reason="resolve_invalid",
                )
                tick_report.record_phase(
                    "resolve_calibration",
                    skip_reason="resolve_invalid",
                )

            with trace.phase("preamble_build_sync_fallback"):
                sync_fallback_by_id = build_target_place_fallback_zero_by_keyword_id(
                    all_contexts,
                    campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                )
            eligibility_by_ks_id = eligibility

        if plan is not None and allows_ladder_phases(campaign_mode):
            assert fact is not None
            if dto is None:
                logger.warning(
                    "[adv_id=%s] v3: no WBAdvDTO, skip post-gate and snapshot "
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
                if plan_fact_change is not None:
                    with trace.phase("cache_plan_fact_snapshot"):
                        await plan_fact_change.set_new_plan_fact(plan, fact)
                if views_cache is not None and current_views is not None:
                    with trace.phase("cache_views_snapshot"):
                        await views_cache.set_views(current_views)
                if (
                    calibration_step_cache is not None
                    and current_calibration_direct is not None
                    and calibration_executed_this_tick
                ):
                    with trace.phase("cache_calibration_step_snapshot"):
                        await calibration_step_cache.set_state(
                            CalibrationStepState(
                                effective_steps=effective_calibration_steps,
                                direct=current_calibration_direct,
                            )
                        )
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
                    "hard_status_sync=%s cap_down=%s passing_up=%s shelf=%s "
                    "realloc=%s enable=%s calibration=%s guard=%s "
                    "post_gate up=%s down=%s off=%s",
                    complex_adv.adv_id,
                    state.name if state else "None",
                    compute_resolve_cost_threshold(plan, fact)
                    if fact is not None
                    else None,
                    fact.pay_for_order if fact else None,
                    preamble_hard_status_sync_count,
                    preamble_cap_down_count,
                    preamble_passing_up_count,
                    preamble_shelf_count,
                    preamble_realloc_count,
                    preamble_enable_count,
                    preamble_calibration_count,
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
        if tick_report_ready and not is_campaign_full_stop(campaign_mode):
            try:
                resolve_for_report: float | None = None
                if plan is not None and fact is not None:
                    candidate = compute_resolve_cost_threshold(plan, fact)
                    if is_resolve_valid(plan, candidate):
                        resolve_for_report = float(candidate)
                fact_cpa = (
                    float(fact.pay_for_order)
                    if fact is not None and fact.pay_for_order is not None
                    else None
                )
                max_pfo = (
                    float(plan.max_pay_for_order)
                    if plan is not None
                    else None
                )
                adv_name = str(getattr(adv, "name", "") or "")
                wl_leader = None
                if ladder_inputs is not None and contexts:
                    prepared_for_report = build_prepared_from_contexts(contexts)
                    wl_leader = find_white_list_cost_leader(
                        contexts,
                        prepared=prepared_for_report,
                        eligibility_by_ks_id=eligibility_by_ks_id,
                        ladder_inputs=ladder_inputs,
                    )
                snapshot = tick_report.build_snapshot(
                    adv_id=int(complex_adv.adv_id),
                    adv_name=adv_name,
                    campaign_mode=campaign_mode.name,
                    sales_state=state.name if state is not None else None,
                    keywords=ledger.keywords,
                    applied=ledger.applied_actions(),
                    fact_cpa=fact_cpa,
                    resolve=resolve_for_report,
                    max_pay_for_order=max_pfo,
                    calibration_effective_steps=(
                        effective_calibration_steps
                        if current_calibration_direct is not None
                        else None
                    ),
                    calibration_direct=(
                        current_calibration_direct.value
                        if current_calibration_direct is not None
                        else None
                    ),
                    calibration_prev_effective_steps=calibration_prev_effective_steps,
                    white_list_cost_leader=wl_leader,
                )
                await persist_v3_tick_report(adv, snapshot)
            except Exception:
                logger.warning(
                    "[adv_id=%s] v3: tick report persist failed",
                    complex_adv.adv_id,
                    exc_info=True,
                )
        if not is_campaign_full_stop(campaign_mode):
            with trace.phase("sync_target_places_once_finally"):
                await _sync_target_places_once()
