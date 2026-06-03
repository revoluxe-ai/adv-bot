"""Снимок стадий последнего V3-тика для UI «Последние действия с ключами».

Collector накапливает фазы в ``process_adv_v3``; snapshot пишется в Redis
(``V3TickReportRedisCache``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

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

    model_config = {"extra": "forbid"}


PHASE_TITLES: dict[str, tuple[str, str]] = {
    "filter": ("0 · Фильтр operable", "—"),
    "hard_status_sync": ("1 · Sync hard_status ↔ mode", "sync"),
    "no_data_bootstrap": ("2 · DATA_BOOTSTRAP", "UP"),
    "cap_down": ("2 · B · cap_down", "DOWN"),
    "passing_up": ("3 · U · passing_up", "UP"),
    "shelf_cleanup": ("4 · S · shelf cleanup", "DOWN, OFF"),
    "max_cpa_guard": ("5 · G · max CPA guard", "DOWN, OFF"),
    "cost_reallocation": ("6 · R · cost_reallocation", "DOWN, REBALANCE"),
    "pay_for_order_gap_enable": ("7 · enable · gap", "UP"),
    "resolve_calibration": ("8 · calibration", "UP, DOWN"),
}


@dataclass
class V3TickReportCollector:
    """Накопитель фаз за один ``process_adv_v3``."""

    aggression_score_before: int = 0
    _phases: list[V3PhaseStats] = field(default_factory=list)
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

    def record_sync(
        self,
        sync_count: int,
        *,
        outcome_note: str | None = None,
    ) -> None:
        title, possible = PHASE_TITLES["hard_status_sync"]
        note = outcome_note
        if sync_count == 0 and note is None:
            note = "режимы уже соответствуют hard_status"
        self._phases.append(
            V3PhaseStats(
                phase_id="hard_status_sync",
                title_ru=title,
                possible_actions_ru=possible,
                sync=sync_count,
                outcome_note=note if sync_count == 0 else None,
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
        )
