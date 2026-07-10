"""Observer preamble: сбор cascade SKIP/APPLY/BLOCK/PASS по operable keywords."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceStep,
    TraceStepStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.status_resolver import (
    resolve_state_label,
    resolve_status_hint,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.base import (
    PreambleExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.phase_report import (
    next_state_steps_for_executor,
    step_to_action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.executor_phase_map import (
    IGNORED_EXECUTOR_NAMES,
    phase_id_for_executor,
    title_ru_for_phase,
)

_DEFAULT_SKIP_REASON = "Причина не зафиксирована в executor'е"


def _empty_trace_steps() -> list[KeywordDecisionTraceStep]:
    return []


def _mode_label(mode: KeywordStrategyMode) -> str:
    return mode.name


@dataclass
class KeywordAccumulator:
    """Накопитель шагов одного operable ключа на тике."""

    dto: KeywordDTO
    keyword_text: str
    processing_started_at: datetime
    state_before: str
    status_hint_before: str
    target_place_before: int
    steps: list[KeywordDecisionTraceStep] = field(default_factory=_empty_trace_steps)


class KeywordDecisionTraceCollector:
    """Observer NORMAL preamble: фиксирует cascade без влияния на pipeline."""

    def __init__(self) -> None:
        self.tick_started_at: datetime | None = None
        self.processing_started_at: datetime | None = None
        self._keywords: dict[int, KeywordAccumulator] = {}

    def start_tick(
        self,
        *,
        tick_started_at: datetime,
        processing_started_at: datetime | None = None,
    ) -> None:
        """Зафиксировать timing тика до цикла executors."""
        self.tick_started_at = tick_started_at
        self.processing_started_at = processing_started_at or tick_started_at

    def register_operable_keywords(
        self,
        keywords: list[KeywordDTO],
        *,
        nmids: list[int] | None = None,
        nmid_display: str = "",
    ) -> None:
        """Зарегистрировать operable keywords до первого executor.

        Args:
            keywords: DTO из ``update_context.keywords``.
            nmids: Артикулы кампании (дублируются в entry).
            nmid_display: Строка для UI.
        """
        _ = nmids, nmid_display
        now = self.processing_started_at or datetime.now(timezone.utc)
        for dto in keywords:
            ks_id = dto.keyword_setting_id
            if ks_id <= 0:
                continue
            self._keywords[ks_id] = KeywordAccumulator(
                dto=dto,
                keyword_text=dto.calculated_keyword.text,
                processing_started_at=now,
                state_before=resolve_state_label(dto),
                status_hint_before=resolve_status_hint(dto),
                target_place_before=dto.current_target_place,
            )

    def record_executor_phase(
        self,
        *,
        context: UpdateContext,
        executor: PreambleExecutor,
        order: int,
        steps_before: dict[int, int],
        tp_steps_before: dict[int, int],
        skip_reason: str | None,
    ) -> None:
        """Записать исход фазы для каждого operable ключа."""
        if not self._keywords:
            return
        executor_name = type(executor).__name__
        if executor_name in IGNORED_EXECUTOR_NAMES:
            return
        phase_id = executor.phase_name
        processed_at = datetime.now(timezone.utc)
        title_ru = title_ru_for_phase(phase_id_for_executor(executor_name))

        for ks_id, acc in self._keywords.items():
            dto = _dto_for_keyword(context, ks_id, fallback=acc.dto)
            step = self._build_step_for_keyword(
                dto=dto,
                ks_id=ks_id,
                executor_name=executor_name,
                phase_id=phase_id,
                order=order,
                title_ru=title_ru,
                steps_before=steps_before.get(ks_id, 0),
                tp_steps_before=tp_steps_before.get(ks_id, 0),
                skip_reason=skip_reason,
                processed_at=processed_at,
            )
            acc.steps.append(step)

    def iter_accumulators(self) -> list[KeywordAccumulator]:
        """Все накопители operable keywords (для builder)."""
        return list(self._keywords.values())

    def operable_count(self) -> int:
        """Число зарегистрированных operable keywords."""
        return len(self._keywords)

    def _build_step_for_keyword(
        self,
        *,
        dto: KeywordDTO,
        ks_id: int,
        executor_name: str,
        phase_id: str,
        order: int,
        title_ru: str,
        steps_before: int,
        tp_steps_before: int,
        skip_reason: str | None,
        processed_at: datetime,
    ) -> KeywordDecisionTraceStep:
        state_after = resolve_state_label(dto)
        status_hint_after = resolve_status_hint(dto)
        target_place_after = dto.current_target_place

        if skip_reason is not None:
            return KeywordDecisionTraceStep(
                order=order,
                phase_id=phase_id,
                executor_name=executor_name,
                status=TraceStepStatus.PASS,
                decision_ru="пропуск фазы",
                reason_ru=skip_reason,
                state_after=state_after,
                status_hint_after=status_hint_after,
                target_place_after=target_place_after,
                processed_at=processed_at,
            )

        mode_steps = next_state_steps_for_executor(
            dto,
            executor_name=executor_name,
            steps_before=steps_before,
        )
        tp_steps = [
            step
            for step in dto.history_target_place[tp_steps_before:]
            if step.executor_name == executor_name
        ]
        has_diff = bool(mode_steps) or bool(tp_steps)

        if not has_diff:
            return KeywordDecisionTraceStep(
                order=order,
                phase_id=phase_id,
                executor_name=executor_name,
                status=TraceStepStatus.SKIP,
                decision_ru="не менять",
                reason_ru=_DEFAULT_SKIP_REASON,
                state_after=state_after,
                status_hint_after=status_hint_after,
                target_place_after=target_place_after,
                processed_at=processed_at,
            )

        is_block = False
        decision_parts: list[str] = []
        reason_parts: list[str] = []

        prior = dto.stored_mode
        idx_before = len(dto.next_state) - len(mode_steps)
        if idx_before > 0:
            prior = dto.next_state[idx_before - 1].new_mode.to_strategy_mode()

        for step in mode_steps:
            if step.executor_name in IGNORED_EXECUTOR_NAMES:
                prior = step.new_mode.to_strategy_mode()
                continue
            new_mode = step.new_mode.to_strategy_mode()
            action = step_to_action(
                ks_id,
                dto=dto,
                prior_mode=prior,
                step=step,
            )
            if action is not None and action.action == V3ActionType.FORCE_OFF:
                is_block = True
                decision_parts.append("FORCE_OFF")
            elif action is not None:
                decision_parts.append(action.action.name)
            else:
                decision_parts.append("MODE")
            body = f"{_mode_label(prior)}→{_mode_label(new_mode)}"
            reason_parts.append(f"{title_ru}: {body}")
            prior = new_mode

        for tp_step in tp_steps:
            decision_parts.append("TARGET_PLACE")
            reason_parts.append(f"{title_ru}: tp → {tp_step.new_target_place}")

        status = (
            TraceStepStatus.BLOCK if is_block else TraceStepStatus.APPLY
        )
        decision_ru = " / ".join(decision_parts) if decision_parts else "изменение"
        reason_ru = "; ".join(reason_parts) if reason_parts else _DEFAULT_SKIP_REASON

        return KeywordDecisionTraceStep(
            order=order,
            phase_id=phase_id,
            executor_name=executor_name,
            status=status,
            decision_ru=decision_ru,
            reason_ru=reason_ru,
            state_after=state_after,
            status_hint_after=status_hint_after,
            target_place_after=target_place_after,
            processed_at=processed_at,
        )


def _dto_for_keyword(
    context: UpdateContext,
    ks_id: int,
    *,
    fallback: KeywordDTO,
) -> KeywordDTO:
    for dto in context.keywords:
        if dto.keyword_setting_id == ks_id:
            return dto
    return fallback
