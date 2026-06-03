"""Матрица ladder-стейтов ключа (OFF/GAP/M/O/C) из CH-профиля."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.v3_ladder_stage_kind import (
    V3LadderStageKind,
)


class TargetPlaceMatrix:
    """Снимок target_place/CPO по ступеням лестницы для одного ключa."""

    __slots__ = ("_states",)

    def __init__(self, states: tuple[KeywordV3LadderState, ...]) -> None:
        self._states = states

    @property
    def states(self) -> tuple[KeywordV3LadderState, ...]:
        """Все ступени матрицы (immutable view)."""
        return self._states

    def for_stage(self, stage: V3LadderStageKind) -> KeywordV3LadderState | None:
        """Стейт ступени или ``None``, если ступень не построена."""
        for state in self._states:
            if state.stage == stage:
                return state
        return None

    def replace_states(self, states: tuple[KeywordV3LadderState, ...]) -> TargetPlaceMatrix:
        """Новая матрица после пересборки ladder (refresh tick state)."""
        return TargetPlaceMatrix(states)
