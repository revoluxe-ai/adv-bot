"""Снимок стадий последнего V3-тика для UI «Последние действия с ключами».

Collector накапливает фазы в ``process_adv_v3``; snapshot пишется в Redis
(``V3TickReportRedisCache``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    AppliedV3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        PreparedListLike,
    )

_HARD_STATUS_WHITE_LIST = 2

_HARD_STATUS_LABELS: dict[int, str] = {
    0: "Не релевантные",
    1: "Авто",
    2: "Белый список",
    3: "Отключен",
    4: "Фикс.фразы",
}


def hard_status_label_ru(hard_status: int) -> str:
    """Русское имя списка по ``hard_status`` (согласовано с UI keyword settings)."""
    return _HARD_STATUS_LABELS.get(int(hard_status), f"hard_status={hard_status}")


def mode_aggression_points(mode: KeywordStrategyMode) -> int:
    """Баллы агрессии: OFF=0, MIN=1, OPT=2, MAX=3."""
    if mode == KeywordStrategyMode.OFF:
        return 0
    if mode == KeywordStrategyMode.MIN_CPA:
        return 1
    if mode == KeywordStrategyMode.OPTIMUM:
        return 2
    if mode == KeywordStrategyMode.MAX_CONVERSION:
        return 3
    return 0


def campaign_aggression_score(keywords: list[CalculatedKeyword]) -> int:
    """Сумма баллов режимов по всем ключам кампании."""
    total = 0
    for kw in keywords:
        total += mode_aggression_points(kw.keyword_setting.strategy_mode)
    return total


def count_hard_status_distribution(
    keywords: list[CalculatedKeyword],
) -> dict[str, int]:
    """Подсчёт ключей по русским названиям hard_status."""
    counts: dict[str, int] = {label: 0 for label in _HARD_STATUS_LABELS.values()}
    for kw in keywords:
        label = hard_status_label_ru(kw.hard_status)
        counts[label] = counts.get(label, 0) + 1
    return {k: v for k, v in counts.items() if v > 0}


class WhiteListCostLeader(BaseModel):
    """Самый дорогой ключ белого списка (hard_status=2) для отчёта тика."""

    keyword_text: str
    keyword_setting_id: int | None = None
    data_tier: str = ""
    strategy_mode: str = ""
    cost_source: str = ""
    decision_cpo: float = 0.0
    state_cpo: float | None = None
    pfo_cpo: float | None = None

    model_config = {"extra": "forbid"}


def find_white_list_cost_leader(
    contexts: list[KeywordV3Context],
    *,
    prepared: PreparedListLike,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
) -> WhiteListCostLeader | None:
    """Ключ БС с максимальным decision CPO (state для FULL, PFO для keyword_pfo).

    Args:
        contexts: контексты кампании (после preamble).
        prepared: operable snapshot для ``resolve_effective_state_cost``.
        eligibility_by_ks_id: tier/eligibility по ks_id.
        ladder_inputs: RK/rec лестница; без неё state CPO не считается.

    Returns:
        Лидер или ``None``, если нет БС с измеримым CPO.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
        stored_strategy_mode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers import (
        resolve_effective_state_cost_for_mode,
    )

    if ladder_inputs is None:
        return None

    best: WhiteListCostLeader | None = None
    best_cpo = -1.0

    for ctx in contexts:
        if int(ctx.keyword.hard_status) != _HARD_STATUS_WHITE_LIST:
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        mode = stored_strategy_mode(ctx.keyword)
        pfo_raw = ctx.keyword.pay_for_order
        pfo_cpo: float | None = None
        if pfo_raw is not None and math.isfinite(float(pfo_raw)) and float(pfo_raw) > 0:
            pfo_cpo = float(pfo_raw)

        state_cpo: float | None = None
        if mode != KeywordStrategyMode.OFF:
            cost, _ = resolve_effective_state_cost_for_mode(
                ctx=ctx,
                to_mode=mode,
                prepared=prepared,
                eligibility_by_ks_id=eligibility_by_ks_id,
                ladder_inputs=ladder_inputs,
            )
            if cost != float("inf") and math.isfinite(float(cost)) and float(cost) > 0:
                state_cpo = float(cost)

        elig = (
            eligibility_by_ks_id.get(ks_id)
            if eligibility_by_ks_id is not None and ks_id > 0
            else None
        )
        tier = elig.data_tier.value if elig is not None else ""
        cost_source = ""
        decision: float | None = None
        if elig is not None and elig.data_tier == KeywordDataTier.KEYWORD_PFO:
            if pfo_cpo is not None:
                decision = pfo_cpo
                cost_source = "pfo"
        elif elig is not None and elig.data_tier == KeywordDataTier.KEYWORD_FULL:
            if state_cpo is not None:
                decision = state_cpo
                cost_source = "state"
        else:
            for value, source in ((state_cpo, "state"), (pfo_cpo, "pfo")):
                if value is not None and value > (decision or -1.0):
                    decision = value
                    cost_source = source

        if decision is None or decision <= best_cpo:
            continue
        best_cpo = decision
        text = (ctx.keyword.text or "").strip()
        if len(text) > 48:
            text = text[:45] + "…"
        best = WhiteListCostLeader(
            keyword_text=text or f"ks_id={ks_id}",
            keyword_setting_id=ks_id if ks_id > 0 else None,
            data_tier=tier,
            strategy_mode=mode.name,
            cost_source=cost_source,
            decision_cpo=decision,
            state_cpo=state_cpo,
            pfo_cpo=pfo_cpo,
        )
    return best


@dataclass(frozen=True)
class V3ActionBreakdown:
    """Счётчики типов действий в одной фазе."""

    planned: int = 0
    up: int = 0
    down: int = 0
    force_off: int = 0
    rebalance: int = 0

    @classmethod
    def from_actions(cls, actions: list[V3Action] | None) -> V3ActionBreakdown:
        if not actions:
            return cls()
        up = down = force_off = rebalance = 0
        for action in actions:
            if action.action == V3ActionType.UP:
                up += 1
            elif action.action == V3ActionType.DOWN:
                down += 1
            elif action.action == V3ActionType.FORCE_OFF:
                force_off += 1
            elif action.action == V3ActionType.REBALANCE_TRANSFER:
                rebalance += 1
        return cls(
            planned=len(actions),
            up=up,
            down=down,
            force_off=force_off,
            rebalance=rebalance,
        )


@dataclass(frozen=True)
class AppliedBreakdown:
    """Итог применённых действий за тик (из ledger)."""

    up: int = 0
    down: int = 0
    force_off: int = 0

    @classmethod
    def from_applied(cls, applied: list[AppliedV3Action]) -> AppliedBreakdown:
        up = down = force_off = 0
        for item in applied:
            if item.action == V3ActionType.UP:
                up += 1
            elif item.action == V3ActionType.DOWN:
                down += 1
            elif item.action == V3ActionType.FORCE_OFF:
                force_off += 1
        return cls(up=up, down=down, force_off=force_off)


class V3PhaseStats(BaseModel):
    """Одна стадия preamble NORMAL / NO_DATA."""

    phase_id: str
    title_ru: str
    possible_actions_ru: str = ""
    executed: bool = True
    skip_reason: str | None = None
    outcome_note: str | None = None
    planned: int = 0
    up: int = 0
    down: int = 0
    force_off: int = 0
    rebalance: int = 0
    sync: int = 0
    ended_off: int = 0
    ended_on: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class V3TickReportSnapshot(BaseModel):
    """Полный отчёт последнего тика V3 для Telegram UI."""

    tick_at: datetime
    adv_id: int
    adv_name: str = ""
    campaign_mode: str
    sales_state: str | None = None
    total_keywords: int = 0
    operable_keywords: int = 0
    fact_cpa: float | None = None
    resolve: float | None = None
    max_pay_for_order: float | None = None
    phases: list[V3PhaseStats] = Field(default_factory=list)
    hard_status_counts: dict[str, int] = Field(default_factory=dict)
    aggression_score_before: int = 0
    aggression_score_after: int = 0
    aggression_delta: int = 0
    net_up: int = 0
    net_down: int = 0
    net_force_off: int = 0
    net_on: int = 0
    calibration_effective_steps: int | None = None
    calibration_applied_steps: int | None = None
    calibration_direct: str | None = None
    calibration_prev_effective_steps: int | None = None
    white_list_cost_leader: WhiteListCostLeader | None = None

    model_config = {"extra": "forbid"}


PHASE_TITLES: dict[str, tuple[str, str]] = {
    "filter": ("0 · Фильтр operable", "—"),
    "validate_state_by_hard_status": ("1 · V · validate hard_status", "OFF"),
    "no_data_bootstrap": ("2 · DATA_BOOTSTRAP", "UP"),
    "validate_not_full_state": ("2 · NF · validate_not_full", "DOWN"),
    "not_full_target_place_migrate": ("2a · NF · tp migrate 0→pos−1", "tp"),
    "not_full_target_place_overspend_reset": (
        "2b · NF · tp overspend → 0",
        "tp",
    ),
    "not_full_target_place_plan_fact": ("2c · NF · tp plan-fact ±1", "tp"),
    "skip_up_same_target_place": ("2d · skip_up · same target_place", "DOWN"),
    "raise_state_to_target_cpo": ("3 · R↑ · raise to resolve", "UP only"),
    "reset_over_max_cpo_on_overspend": ("4 · R↓ · reset over max CPO", "DOWN, OFF"),
    "passing_up": ("5 · U · passing_up", "UP"),
    "shelf_cleanup": ("6 · S · shelf cleanup", "DOWN, OFF"),
    "max_cpa_guard": ("7 · G · max CPA guard", "DOWN, OFF"),
    "cost_reallocation": ("8 · R · cost_reallocation", "DOWN, REBALANCE"),
    "pay_for_order_gap_enable": ("9 · enable · gap", "UP"),
    "pay_for_order_over_max_off_on_deep_overspend": (
        "9b · pfo_off · deep overspend",
        "OFF",
    ),
    "resolve_calibration": ("10 · calibration", "UP, DOWN"),
}


@dataclass
class V3TickReportCollector:
    """Накопитель фаз за один ``process_adv_v3``."""

    aggression_score_before: int = 0
    _phases: list[V3PhaseStats] = field(
        default_factory=lambda: list[V3PhaseStats]()
    )
    _total_keywords: int = 0
    _operable_keywords: int = 0

    def set_aggression_before(self, keywords: list[CalculatedKeyword]) -> None:
        self.aggression_score_before = campaign_aggression_score(keywords)

    def record_filter(self, *, total: int, operable: int) -> None:
        self._total_keywords = total
        self._operable_keywords = operable
        title, possible = PHASE_TITLES["filter"]
        self._phases.append(
            V3PhaseStats(
                phase_id="filter",
                title_ru=title,
                possible_actions_ru=possible,
                extra={"total": total, "operable": operable},
            )
        )

    def record_phase(
        self,
        phase_id: str,
        actions: list[V3Action] | None = None,
        *,
        skip_reason: str | None = None,
        executed: bool = True,
        sync_count: int = 0,
        outcome_note: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Зафиксировать фазу с breakdown действий, пропуска или нулевого исхода."""
        meta = PHASE_TITLES.get(phase_id)
        if meta is None:
            title, possible = phase_id, ""
        else:
            title, possible = meta
        if skip_reason is not None:
            self._phases.append(
                V3PhaseStats(
                    phase_id=phase_id,
                    title_ru=title,
                    possible_actions_ru=possible,
                    executed=False,
                    skip_reason=skip_reason,
                    extra=extra or {},
                )
            )
            return
        breakdown = V3ActionBreakdown.from_actions(actions)
        note = outcome_note
        if breakdown.planned == 0 and note is None:
            note = "планировщик не выбрал ключей"
        self._phases.append(
            V3PhaseStats(
                phase_id=phase_id,
                title_ru=title,
                possible_actions_ru=possible,
                executed=executed,
                planned=breakdown.planned,
                up=breakdown.up,
                down=breakdown.down,
                force_off=breakdown.force_off,
                rebalance=breakdown.rebalance,
                sync=sync_count,
                outcome_note=note if breakdown.planned == 0 else None,
                extra=extra or {},
            )
        )

    def build_snapshot(
        self,
        *,
        adv_id: int,
        adv_name: str,
        campaign_mode: str,
        sales_state: str | None,
        keywords: list[CalculatedKeyword],
        applied: list[AppliedV3Action],
        fact_cpa: float | None = None,
        resolve: float | None = None,
        max_pay_for_order: float | None = None,
        tick_at: datetime | None = None,
        calibration_effective_steps: int | None = None,
        calibration_applied_steps: int | None = None,
        calibration_direct: str | None = None,
        calibration_prev_effective_steps: int | None = None,
        white_list_cost_leader: WhiteListCostLeader | None = None,
    ) -> V3TickReportSnapshot:
        """Собрать финальный snapshot для Redis."""
        aggression_after = campaign_aggression_score(keywords)
        applied_bd = AppliedBreakdown.from_applied(applied)
        ts = tick_at or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return V3TickReportSnapshot(
            tick_at=ts,
            adv_id=adv_id,
            adv_name=adv_name,
            campaign_mode=campaign_mode,
            sales_state=sales_state,
            total_keywords=self._total_keywords,
            operable_keywords=self._operable_keywords,
            fact_cpa=fact_cpa,
            resolve=resolve,
            max_pay_for_order=max_pay_for_order,
            phases=list(self._phases),
            hard_status_counts=count_hard_status_distribution(keywords),
            aggression_score_before=self.aggression_score_before,
            aggression_score_after=aggression_after,
            aggression_delta=aggression_after - self.aggression_score_before,
            net_up=applied_bd.up,
            net_down=applied_bd.down,
            net_force_off=applied_bd.force_off,
            calibration_effective_steps=calibration_effective_steps,
            calibration_applied_steps=calibration_applied_steps,
            calibration_direct=calibration_direct,
            calibration_prev_effective_steps=calibration_prev_effective_steps,
            white_list_cost_leader=white_list_cost_leader,
        )
