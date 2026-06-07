"""NORMAL preamble: ``UpdatePipelineManager.run_preamble`` (in-place ``NextState``)."""

from __future__ import annotations

import logging

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline import (
    UpdatePipeline,
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    PreambleExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.phase_report import (
    next_state_steps_for_executor,
    steps_to_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.runner import (
    PreamblePipelineRunResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_phase_notes import (
    summarize_phase_zero_actions,
)

logger = logging.getLogger(__name__)

_PHASE_LOG: dict[str, tuple[str, str]] = {
    "validate_state_by_hard_status": ("v3 VALIDATE_HARD_STATUS", "validate_count"),
    "not_full_target_place_migrate": (
        "v3 NOT_FULL_TP_MIGRATE",
        "not_full_target_place_migrate_count",
    ),
    "validate_not_full_state": ("v3 VALIDATE_NOT_FULL", "validate_not_full_count"),
    "not_full_target_place_overspend_reset": (
        "v3 NOT_FULL_TP_OVERSPEND",
        "not_full_target_place_overspend_reset_count",
    ),
    "not_full_target_place_plan_fact": (
        "v3 NOT_FULL_TP_PLAN_FACT",
        "not_full_target_place_plan_fact_count",
    ),
    "raise_state_to_target_cpo": ("v3 RAISE_STATE_TO_TARGET_CPO", "raise_state_count"),
    "reset_over_max_cpo_on_overspend": (
        "v3 RESET_OVER_MAX_CPO",
        "reset_over_max_cpo_count",
    ),
    "shelf_cleanup": ("v3 SHELF_REC_CLEANUP", "shelf_count"),
    "cost_reallocation": ("v3 COST_REALLOCATION", "realloc_count"),
    "pay_for_order_gap_enable": ("v3 PAY_FOR_ORDER_GAP_ENABLE", "enable_count"),
    "pay_for_order_over_max_off_on_deep_overspend": (
        "v3 PAY_FOR_ORDER_OVER_MAX_OFF",
        "pfo_off_count",
    ),
    "resolve_calibration": ("v3 RESOLVE_CALIBRATION", "calibration_count"),
}


def _executor_extra(context: UpdateContext, executor: PreambleExecutor) -> dict[str, object] | None:
    state = context.adv_state
    if executor.phase_name == "resolve_calibration":
        return dict(state.calibration_phase_extra)
    if executor.phase_name == "shelf_cleanup" and state.shelf_active:
        return {"shelf_active": True}
    return None


def _steps_before(context: UpdateContext) -> dict[int, int]:
    return {dto.keyword_setting_id: len(dto.next_state) for dto in context.keywords}


def _target_place_steps_before(context: UpdateContext) -> dict[int, int]:
    return {
        dto.keyword_setting_id: len(dto.history_target_place)
        for dto in context.keywords
    }


def _count_target_place_steps_for_executor(
    context: UpdateContext,
    *,
    executor_name: str,
    steps_before: dict[int, int],
) -> int:
    """Число новых ``history_target_place`` записей executor на тике."""
    touched = 0
    for dto in context.keywords:
        before = steps_before.get(dto.keyword_setting_id, 0)
        for step in dto.history_target_place[before:]:
            if step.executor_name == executor_name:
                touched += 1
    return touched


def _actions_for_executor_phase(
    context: UpdateContext,
    *,
    executor_name: str,
    steps_before: dict[int, int],
) -> list[V3Action]:
    actions: list[V3Action] = []
    for dto in context.keywords:
        ks_id = dto.keyword_setting_id
        steps = next_state_steps_for_executor(
            dto,
            executor_name=executor_name,
            steps_before=steps_before.get(ks_id, 0),
        )
        actions.extend(steps_to_v3_actions(dto, steps))
    return actions


def _validate_phase_extra(
    context: UpdateContext,
    *,
    steps_before: dict[int, int],
) -> dict[str, object]:
    touched = 0
    for dto in context.keywords:
        if dto.hard_status != HARD_STATUS_AUTO_MODE:
            continue
        before = steps_before.get(dto.keyword_setting_id, 0)
        if len(dto.next_state) > before:
            touched += 1
    return {"hs1_touched": touched}


def _phase_outcome_note(
    phase_id: str,
    actions: list[V3Action],
    *,
    prepared: PreparedList,
    state: AdvState,
) -> str | None:
    """Примечание для tick report, если фаза не вернула actions."""
    if actions:
        return None
    return summarize_phase_zero_actions(
        phase_id,
        prepared=prepared,
        eligibility_by_ks_id=state.eligibility_by_ks_id,
        resolve=state.resolve,
        policy=state.policy,
        ladder_inputs=state.ladder_inputs,
        shelf_active=state.shelf_active,
        shelf_click_mode=state.shelf_click_mode,
        aggressiveness=state.aggressiveness,
        max_pay_for_order=state.max_pay_for_order,
        fact_pay_for_order=state.fact_pay_for_order,
        plan_fact_changed=state.plan_fact_changed,
        views_changed=state.views_changed,
        calibration_direct=state.calibration_direct,
        max_effective_steps=state.max_effective_steps,
    )


class UpdatePipelineManager:
    """Прогон NORMAL preamble: executors in-place → ``NextState`` на ``KeywordDTO``."""

    def run_preamble(self, update_context: UpdateContext) -> PreamblePipelineRunResult:
        """V → B → U → S → G → R → enable → calibration."""
        rt = update_context.runtime
        if rt is None:
            raise ValueError("UpdateContext.runtime is required for preamble")

        current_ctx = update_context
        state = current_ctx.adv_state
        stats = PreamblePipelineRunResult(
            update_context=current_ctx,
            contexts=rt.contexts,
            all_contexts=rt.all_contexts,
            prepared=current_ctx.prepared,
            eligibility=state.eligibility_by_ks_id,
            ladder_inputs=state.ladder_inputs,
        )

        for executor in UpdatePipeline(build_normal_preamble_executors()).executors:
            prepared_before = current_ctx.keyword_batch.to_legacy_prepared()
            steps_before = _steps_before(current_ctx)
            tp_steps_before = _target_place_steps_before(current_ctx)
            executor.execute(current_ctx)
            state = current_ctx.adv_state
            extra = _executor_extra(current_ctx, executor)

            skip_reason = getattr(executor, "skip_reason", None)
            if skip_reason is not None:
                if executor.phase_name == "resolve_calibration":
                    stats.calibration_reset_required = True
                rt.tick_report.record_phase(
                    executor.phase_name,
                    skip_reason=skip_reason,
                    extra=extra,
                )
                if executor.phase_name == "resolve_calibration":
                    logger.debug(
                        "[adv_id=%s] v3 RESOLVE_CALIBRATION skipped: %s",
                        rt.adv_id,
                        skip_reason,
                    )
                continue

            executor_name = type(executor).__name__
            actions = _actions_for_executor_phase(
                current_ctx,
                executor_name=executor_name,
                steps_before=steps_before,
            )
            if executor.phase_name == "validate_state_by_hard_status":
                validate_extra = _validate_phase_extra(
                    current_ctx,
                    steps_before=steps_before,
                )
                extra = {**(extra or {}), **validate_extra}

            rt.tick_report.record_phase(
                executor.phase_name,
                actions,
                extra=extra,
                outcome_note=_phase_outcome_note(
                    executor.phase_name,
                    actions,
                    prepared=prepared_before,
                    state=state,
                ),
            )

            if executor.phase_name == "resolve_calibration":
                stats.calibration_executed = True

            log_label, stat_field = _PHASE_LOG.get(
                executor.phase_name,
                (f"v3 {executor.phase_name.upper()}", ""),
            )
            if actions:
                if executor.phase_name == "resolve_calibration" and state.calibration_direct:
                    logger.info(
                        "[adv_id=%s] %s (%s): actions=%s",
                        rt.adv_id,
                        log_label,
                        state.calibration_direct.value,
                        len(actions),
                    )
                else:
                    logger.info(
                        "[adv_id=%s] %s: actions=%s",
                        rt.adv_id,
                        log_label,
                        len(actions),
                    )
            if stat_field and actions:
                setattr(stats, stat_field, getattr(stats, stat_field) + len(actions))
            elif stat_field in (
                "not_full_target_place_migrate_count",
                "not_full_target_place_overspend_reset_count",
                "not_full_target_place_plan_fact_count",
            ):
                tp_touched = _count_target_place_steps_for_executor(
                    current_ctx,
                    executor_name=executor_name,
                    steps_before=tp_steps_before,
                )
                if tp_touched:
                    setattr(
                        stats,
                        stat_field,
                        getattr(stats, stat_field) + tp_touched,
                    )
            elif stat_field == "validate_count" and extra:
                hs1_touched = extra.get("hs1_touched")
                if isinstance(hs1_touched, int):
                    setattr(stats, stat_field, hs1_touched)

        stats.update_context = current_ctx
        return stats
