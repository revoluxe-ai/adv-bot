"""Один ladder-state ключа V3 (M/O/C, OFF, GAP)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)


@dataclass(frozen=True, slots=True)
class KeywordV3LadderState:
    """Полноценный state: режим, ``target_position``, CPO (для NO DATA — PFO на MIN)."""

    keyword_setting_id: int
    stage: V3LadderStageKind
    strategy_mode: KeywordStrategyMode
    target_position: int
    cpo: float | None
    is_valid: bool = True
    cost_imputed: bool = False
    synthetic_no_data: bool = False

    @property
    def is_gap(self) -> bool:
        """``True`` для ступени GAP (enable NO DATA без профиля)."""
        return self.stage == V3LadderStageKind.GAP

    @property
    def is_no_data_singleton(self) -> bool:
        """Синтетический singleton для NO DATA без CH-матрицы."""
        return self.synthetic_no_data
