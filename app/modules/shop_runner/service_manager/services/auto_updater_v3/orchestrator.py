"""AutoUpdater v3 orchestration (per-keyword aggression).

Порядок на **каждом** тике (``CampaignMode``):
  1. ``DataUpdateManager.load`` — CH/WB, plan/fact, operable contexts.
  2. ``NOT_READY`` — full stop.
  3. ``NO_DATA`` — DATA_BOOTSTRAP → ``ApplyManager``.
  4. ``NORMAL`` — ``UpdateContextManager`` → ``UpdatePipelineManager`` → ``ApplyManager``.

Наблюдаемость: ``v3_selection`` и ``docks/V3_UPDATER_VALIDATION.md``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager import (
    ApplyManager,
    V3ApplyInput,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager import (
    DataUpdateManager,
    TickData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.tick_context import (
    apply_v3_phase_operable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_target_place_fallback_zero_by_keyword_id,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    plan_campaign_no_data_bootstrap_safe,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold import (
    compute_resolve_cost_threshold,
    is_resolve_valid,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    PreparedListLike,
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline import (
    PreamblePipelineRunResult,
    UpdatePipelineManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
    is_campaign_full_stop,
    needs_apply_manager,
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report import (
    build_from_applied_actions,
    build_keyword_changes_snapshot,
    merge_keyword_changes_into_tick_snapshot,
    persist_v3_keyword_changes,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace import (
    KeywordDecisionTraceCollector,
    build_keyword_decision_trace_snapshot,
    persist_keyword_decision_trace,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

logger = logging.getLogger(__name__)


def _phase_outcome_note_if_empty(
    phase_id: str,
    actions: list[V3Action],
    *,
    prepared: PreparedList | PreparedListLike,
    **kwargs: Any,
) -> str | None:
    """Русская причина нулевого исхода фазы; ``None`` если есть действия."""
    if actions:
        return None
    return summarize_phase_zero_actions(phase_id, prepared=prepared, **kwargs)


def _sync_tick_data_after_pipeline(
    tick_data: TickData,
    pipeline_result: PreamblePipelineRunResult,
) -> None:
    """Обновить ``V3TickData`` после preamble (eligibility/ladder; contexts — в ApplyManager)."""
    _ = pipeline_result.contexts
    _ = pipeline_result.all_contexts
    tick_data.ladder_inputs = pipeline_result.ladder_inputs
    tick_data.eligibility_by_ks_id = pipeline_result.eligibility
    if tick_data.tick_input is not None:
        tick_data.tick_input.calibration_phase_extra = dict(
            pipeline_result.update_context.adv_state.calibration_phase_extra
        )
    if tick_data.tick_input is not None and tick_data.tick_input.campaign_orders_per_cart_7d is not None:
        ti = tick_data.tick_input
        tick_data.sync_fallback_by_id = build_target_place_fallback_zero_by_keyword_id(
            tick_data.all_contexts,
            campaign_orders_per_cart_7d=ti.campaign_orders_per_cart_7d,
        )


def only_relevant_phrase_filter(keywords: list[CalculatedKeyword]) -> list[CalculatedKeyword]:
    only_relevant_phrase: list[CalculatedKeyword] = []
    for kw in keywords:
        if kw.relevant:
            only_relevant_phrase.append(kw)
    return only_relevant_phrase


async def process_adv_v3(
    complex_adv: ComplexAdv,
    *,
    wb_shop_data_manager: WBShopDataManager,
    max_last_period: int = 2,
) -> None:
    """Один тик V3: data load → context/pipeline → apply → tick report."""
    tick_report = V3TickReportCollector()
    data_mgr = DataUpdateManager()
    ctx_mgr = UpdateContextManager()
    apply_mgr = ApplyManager()

    tick_data: TickData | None = None
    pipeline_result: PreamblePipelineRunResult | None = None
    trace_collector: KeywordDecisionTraceCollector | None = None
    sync_force_zero = False
    calibration_executed = False

    try:
        keywords = await complex_adv.get_keywords()
        tick_report.set_aggression_before(keywords)
        if complex_adv.auto_add_only_relevant_phrase:
            keywords = only_relevant_phrase_filter(keywords)
        tick_data = await data_mgr.load(
            complex_adv,
            keywords=keywords,
            wb_shop_data_manager=wb_shop_data_manager,
            max_last_period=max_last_period,
            tick_report=tick_report,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt import (
            abort_ordinary_v3_if_enter_signaled,
        )

        # Spec card-ab-hold-mode: interrupt after load (before preamble/apply).
        if await abort_ordinary_v3_if_enter_signaled(complex_adv.adv_setting):
            logger.info(
                "[adv_id=%s] v3: aborted after load (CardAbHold ENTER)",
                complex_adv.adv_id,
            )
            return

        if is_campaign_full_stop(tick_data.campaign_mode):
            logger.info(
                "[adv_id=%s] v3 NOT_READY: full stop (no bootstrap, flush, sync)",
                complex_adv.adv_id,
            )
            return

        if tick_data.campaign_mode == CampaignMode.NO_DATA and tick_data.dto is not None:
            bootstrap_actions = plan_campaign_no_data_bootstrap_safe(tick_data.contexts)
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
                logger.info(
                    "[adv_id=%s] v3 DATA_BOOTSTRAP (NO_DATA): actions=%s",
                    complex_adv.adv_id,
                    len(bootstrap_actions),
                )
                tick_data.contexts, tick_data.all_contexts = apply_v3_phase_operable(
                    tick_data.ledger,
                    bootstrap_actions,
                    tick_data.raw_profiles,
                )
            sync_force_zero = True

        elif tick_data.campaign_mode == CampaignMode.NORMAL and tick_data.dto is not None:
            assert tick_data.tick_input is not None
            update_ctx = ctx_mgr.build_for_tick(tick_data, tick_report=tick_report)
            tick_started_at = datetime.now(timezone.utc)
            trace_collector = KeywordDecisionTraceCollector()
            trace_collector.start_tick(tick_started_at=tick_started_at)
            pipeline_result = UpdatePipelineManager().run_preamble(
                update_ctx,
                trace_collector=trace_collector,
            )
            calibration_executed = pipeline_result.calibration_executed
            _sync_tick_data_after_pipeline(tick_data, pipeline_result)

        if (
            tick_data.tick_input is not None
            and needs_apply_manager(tick_data.campaign_mode)
        ):
            if await abort_ordinary_v3_if_enter_signaled(complex_adv.adv_setting):
                logger.info(
                    "[adv_id=%s] v3: skipped apply after CardAbHold ENTER interrupt",
                    complex_adv.adv_id,
                )
            elif tick_data.dto is None:
                logger.warning(
                    "[adv_id=%s] v3: no WBAdvDTO, skip post-gate and snapshot "
                    "(retry next cycle)",
                    complex_adv.adv_id,
                )
            else:
                await apply_mgr.apply(
                    V3ApplyInput(
                        tick_data=tick_data,
                        update_context=(
                            pipeline_result.update_context if pipeline_result else None
                        ),
                        pipeline_result=pipeline_result,
                        calibration_executed=calibration_executed,
                        sync_force_zero=sync_force_zero,
                    )
                )

    finally:
        if (
            tick_data is not None
            and tick_data.tick_report_ready
            and not is_campaign_full_stop(tick_data.campaign_mode)
        ):
            try:
                tick_input = tick_data.tick_input
                assert tick_input is not None
                plan = tick_input.plan
                fact = tick_input.fact
                resolve_for_report: float | None = None
                candidate = compute_resolve_cost_threshold(plan, fact)
                if is_resolve_valid(plan, candidate):
                    resolve_for_report = float(candidate)
                fact_cpa = (
                    float(fact.pay_for_order)
                    if fact.pay_for_order is not None
                    else None
                )
                max_pfo = float(plan.max_pay_for_order)
                adv_name = str(
                    getattr(tick_data.complex_adv.adv_setting, "name", "") or ""
                )
                wl_leader = None
                if tick_data.ladder_inputs is not None and tick_data.contexts:
                    prepared_for_report = build_prepared_from_contexts(
                        tick_data.contexts
                    )
                    wl_leader = find_white_list_cost_leader(
                        tick_data.contexts,
                        prepared=prepared_for_report,
                        eligibility_by_ks_id=tick_data.eligibility_by_ks_id,
                        ladder_inputs=tick_data.ladder_inputs,
                    )
                calibration_extra = tick_input.calibration_phase_extra
                snapshot = tick_report.build_snapshot(
                    adv_id=int(complex_adv.adv_id),
                    adv_name=adv_name,
                    campaign_mode=tick_data.campaign_mode.name,
                    sales_state=(
                        tick_data.sales_state.name
                        if tick_data.sales_state is not None
                        else None
                    ),
                    keywords=tick_data.ledger.keywords,
                    applied=tick_data.ledger.applied_actions(),
                    fact_cpa=fact_cpa,
                    resolve=resolve_for_report,
                    max_pay_for_order=max_pfo,
                    calibration_effective_steps=(
                        tick_input.max_effective_steps
                        if tick_input.calibration_direct is not None
                        else None
                    ),
                    calibration_applied_steps=(
                        _applied
                        if isinstance(
                            (_applied := calibration_extra.get("applied_steps")),
                            int,
                        )
                        else None
                    ),
                    calibration_direct=(
                        tick_input.calibration_direct.value
                        if tick_input.calibration_direct is not None
                        else None
                    ),
                    calibration_prev_effective_steps=(
                        _prev
                        if isinstance(
                            (_prev := calibration_extra.get("prev_effective_steps")),
                            int,
                        )
                        else None
                    ),
                    white_list_cost_leader=wl_leader,
                )
                audit = None
                if pipeline_result is not None:
                    audit = build_keyword_changes_snapshot(
                        pipeline_result.update_context.keywords,
                        adv_id=int(complex_adv.adv_id),
                        tick_at=snapshot.tick_at,
                    )
                elif tick_data.campaign_mode == CampaignMode.NO_DATA:
                    audit = build_from_applied_actions(
                        tick_data.ledger.applied_actions(),
                        adv_id=int(complex_adv.adv_id),
                        tick_at=snapshot.tick_at,
                        keywords_aggression_modes=[
                            kw.keyword_setting.strategy_mode
                            for kw in tick_data.ledger.keywords
                        ],
                    )
                if audit is not None:
                    snapshot = merge_keyword_changes_into_tick_snapshot(
                        snapshot,
                        audit,
                    )
                    await persist_v3_keyword_changes(
                        tick_data.complex_adv.adv_setting,
                        audit,
                    )
                if pipeline_result is not None and trace_collector is not None:
                    adv_setting = tick_data.complex_adv.adv_setting
                    tick_finished_at = datetime.now(timezone.utc)
                    trace_snapshot = build_keyword_decision_trace_snapshot(
                        trace_collector,
                        adv_id=int(complex_adv.adv_id),
                        tick_finished_at=tick_finished_at,
                        nmids=list(adv_setting.nmids or []),
                    )
                    await persist_keyword_decision_trace(
                        adv_setting,
                        trace_snapshot,
                    )
                await persist_v3_tick_report(
                    tick_data.complex_adv.adv_setting,
                    snapshot,
                )
            except Exception:
                logger.warning(
                    "[adv_id=%s] v3: tick report persist failed",
                    complex_adv.adv_id,
                    exc_info=True,
                )
        if tick_data is not None and not is_campaign_full_stop(tick_data.campaign_mode):
            await apply_mgr.sync_target_places_if_needed(
                tick_data,
                sync_force_zero=sync_force_zero,
            )
