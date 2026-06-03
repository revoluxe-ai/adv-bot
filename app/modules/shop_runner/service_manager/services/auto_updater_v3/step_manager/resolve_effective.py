"""Resolve одного effective UP/DOWN по ``current`` + catalog (без списка ключей)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    count_effective_released_aggression_steps,
    resolve_next_effective_step_down,
    resolve_next_effective_step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.dto import (
    EffectiveDown,
    EffectiveUp,
)


def resolve_effective_down(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> EffectiveDown:
    """Один effective DOWN: следующий режим с другим ``target_place`` или OFF."""
    res = resolve_next_effective_step_down(current, catalog)
    released = count_effective_released_aggression_steps(
        current,
        res.next_mode,
        catalog,
    )
    return EffectiveDown(
        from_mode=current,
        to_mode=res.next_mode,
        skipped_aliases=res.skipped_aliases,
        released_aggression_steps=released,
    )


def resolve_effective_up(
    current: KeywordStrategyMode,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> EffectiveUp:
    """Один effective UP: следующий режим с другим ``target_place``."""
    res = resolve_next_effective_step_up(current, catalog)
    return EffectiveUp(
        from_mode=current,
        to_mode=res.next_mode,
        skipped_aliases=res.skipped_aliases,
    )
