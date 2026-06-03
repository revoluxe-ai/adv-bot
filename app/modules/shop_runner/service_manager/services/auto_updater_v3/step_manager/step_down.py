"""DOWN по списку ключей: пул состояний → sort → pick → bump ``UpdateContext``."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.dto import (
    StepCandidate,
    StepRunBatchResult,
    StepRunResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.prepared_state import (
    bump_prepared_mode,
)


def run_step_down(
    context: UpdateContext,
    *,
    collect: Callable[[UpdateContext], Sequence[StepCandidate]],
    sort_key: Callable[[StepCandidate], tuple[float, ...]],
) -> StepRunResult[StepCandidate]:
    """Одна итерация DOWN: пул → pick → обновление ``active_mode`` + history."""
    pool = list(collect(context))
    if not pool:
        return StepRunResult(context=context.copy(), pick=None, pool_size=0)
    best = min(pool, key=sort_key)
    if best.to_mode == best.from_mode:
        return StepRunResult(context=context.copy(), pick=None, pool_size=len(pool))
    updated = bump_prepared_mode(context, best.keyword_setting_id, best.to_mode)
    return StepRunResult(context=updated, pick=best, pool_size=len(pool))


def run_steps_down(
    context: UpdateContext,
    budget: int,
    *,
    collect: Callable[[UpdateContext], Sequence[StepCandidate]],
    sort_key: Callable[[StepCandidate], tuple[float, ...]],
    on_pick: Callable[[StepCandidate, UpdateContext, int], None] | None = None,
) -> StepRunBatchResult[StepCandidate]:
    """До ``budget`` итераций DOWN с пересбором пула после каждого шага."""
    working = context.copy()
    picks: list[StepCandidate] = []
    step_budget = max(1, int(budget))
    for _ in range(step_budget):
        result = run_step_down(working, collect=collect, sort_key=sort_key)
        if result.pick is None:
            break
        if on_pick is not None:
            on_pick(result.pick, working, result.pool_size)
        working = result.context
        picks.append(result.pick)
    return StepRunBatchResult(context=working, picks=picks)
