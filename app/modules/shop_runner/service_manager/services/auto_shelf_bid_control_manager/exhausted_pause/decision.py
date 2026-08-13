"""Чистые решения terminal shelf-exhausted pause (detect / clear / gate).

Spec: ``auto-shelf-exhausted-pause``.
Зачем: detect/ordering отделены от WB pause (pause = activity-control).
ADL: ``auto-shelf-exhausted-pause-write-path`` (proposed).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AutoReasonCode,
)

DEFAULT_RETEST_INTERVAL_DAYS = 7

ResolveCpoKind = Literal["target", "max"]


@dataclass(frozen=True)
class TerminalDetectInput:
    """Входы terminal detect на тике полок."""

    module_enabled: bool
    strategy: AutoShelfBidControlStrategy | str | None
    next_test_bid_minor: int | None
    plan_ranked: Sequence[Mapping[str, object]] | None
    qualified_tested_bid_minors: Sequence[int] | None
    resolve_cpo_value: float | None
    resolve_cpo_kind: ResolveCpoKind | None


@dataclass(frozen=True)
class TerminalDetectResult:
    """Результат terminal detect: latch или no-op."""

    should_latch: bool
    reason: str
    has_plan_fit: bool
    epoch_exhausted: bool


def gate_allows_shelf_exhausted_path(
    *,
    module_enabled: bool,
    strategy: AutoShelfBidControlStrategy | str | None,
) -> bool:
    """True только при module ON + Best plan (``plan_distance``)."""
    if not module_enabled:
        return False
    if strategy is None:
        return False
    value = strategy.value if isinstance(strategy, AutoShelfBidControlStrategy) else str(strategy)
    return value == AutoShelfBidControlStrategy.PLAN_DISTANCE.value


def _as_mapping_sequence(
    rows: Sequence[Mapping[str, object]] | None,
) -> list[Mapping[str, object]]:
    if not rows:
        return []
    return list(rows)


def has_resolve_cpo_plan_fit(
    *,
    plan_ranked: Sequence[Mapping[str, object]] | None,
    qualified_tested_bid_minors: Sequence[int] | None,
    resolve_cpo_value: float | None,
) -> bool:
    """Есть ли qualified-tested ставка с expected CPO ≤ resolve CPO.

    Spec: не «всегда Max» — порог передаётся уже как текущий resolve.
    Если qualified-список None — учитываем все строки plan_ranked.
    """
    if resolve_cpo_value is None:
        return False
    qualified: set[int] | None = None
    if qualified_tested_bid_minors is not None:
        qualified = {int(b) for b in qualified_tested_bid_minors}
    for row in _as_mapping_sequence(plan_ranked):
        bid_raw = row.get("bid")
        cpo_raw = row.get("cpo_rub")
        if bid_raw is None or cpo_raw is None:
            continue
        try:
            bid = int(cast(Any, bid_raw))
            cpo = float(cast(Any, cpo_raw))
        except (TypeError, ValueError):
            continue
        if qualified is not None and bid not in qualified:
            continue
        if cpo <= float(resolve_cpo_value):
            return True
    return False


def should_latch_terminal_block(inp: TerminalDetectInput) -> TerminalDetectResult:
    """Нужен ли latch PG our-block на этом тике."""
    if not gate_allows_shelf_exhausted_path(
        module_enabled=inp.module_enabled,
        strategy=inp.strategy,
    ):
        return TerminalDetectResult(
            should_latch=False,
            reason="gate_closed",
            has_plan_fit=False,
            epoch_exhausted=False,
        )
    epoch_exhausted = inp.next_test_bid_minor is None
    plan_fit = has_resolve_cpo_plan_fit(
        plan_ranked=inp.plan_ranked,
        qualified_tested_bid_minors=inp.qualified_tested_bid_minors,
        resolve_cpo_value=inp.resolve_cpo_value,
    )
    if not epoch_exhausted:
        return TerminalDetectResult(
            should_latch=False,
            reason="still_have_bids_to_test",
            has_plan_fit=plan_fit,
            epoch_exhausted=False,
        )
    if plan_fit:
        return TerminalDetectResult(
            should_latch=False,
            reason="has_resolve_cpo_plan_fit",
            has_plan_fit=True,
            epoch_exhausted=True,
        )
    if inp.resolve_cpo_value is None or inp.resolve_cpo_kind is None:
        return TerminalDetectResult(
            should_latch=False,
            reason="resolve_cpo_unavailable",
            has_plan_fit=False,
            epoch_exhausted=True,
        )
    return TerminalDetectResult(
        should_latch=True,
        reason="exhausted_no_plan_fit",
        has_plan_fit=False,
        epoch_exhausted=True,
    )


def clear_our_block_due_to_plan_fit(*, block_active: bool, has_plan_fit: bool) -> bool:
    """Снять наш блок при появлении проходных на тике (без forced start)."""
    return bool(block_active) and bool(has_plan_fit)


def clear_our_block_due_to_calendar(
    *,
    block_active: bool,
    due_at: datetime | None,
    now: datetime,
) -> bool:
    """Снять наш блок по календарному due (без forced start)."""
    if not block_active or due_at is None:
        return False
    return now >= due_at


def is_shelf_exhausted_reason(reason_code: Any) -> bool:
    """True если Auto-lane reason = shelf_exhausted_no_plan."""
    if reason_code is None:
        return False
    if reason_code == AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN:
        return True
    return getattr(reason_code, "value", None) == (
        AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN.value
    )


def coverage_date_from_for_epoch(
    *,
    now: datetime,
    epoch_start: datetime | None,
    stats_window_days: int = 7,
) -> datetime:
    """``date_from = max(now - window, epoch_start)`` для новой эпохи."""
    from datetime import timedelta

    window_start = now - timedelta(days=int(stats_window_days))
    if epoch_start is None:
        return window_start
    return max(window_start, epoch_start)


def parse_plan_ranked_rows(recommendation: Mapping[str, object] | None) -> list[dict[str, object]]:
    """Извлечь plan_ranked rows из rec recommendation mapping."""
    if recommendation is None:
        return []
    raw = recommendation.get("plan_ranked")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return []
    out: list[dict[str, object]] = []
    for item in cast(Iterable[object], raw):
        if isinstance(item, Mapping):
            typed_item = cast(Mapping[object, object], item)
            out.append({str(k): v for k, v in typed_item.items()})
    return out
