"""Adaptive effective steps для калибровки (×2/÷2 по ветке UP/DOWN).

Калибровка — самостоятельный степ preamble: за тик выполняется **одна** ветка,
цель — CPA кампании у **0.9×resolve** (``MAX_PAY_STABILIZATION_RATIO``):

- **ветка UP** — ``fact < 0.9×resolve``: один ключ, следующий effective-шаг (min CPO);
- **ветка DOWN** — ``fact >= 0.9×resolve``: limited trim к ``resolve`` (adaptive steps).

``CalibrationDirect`` (``loosen`` / ``tighten`` в Redis и логах) — legacy-имена веток UP/DOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)


class CalibrationDirect(StrEnum):
    """Ветка калибровки за тик (строки ``loosen``/``tighten`` — legacy в Redis/UI)."""

    LOOSEN = "loosen"  # ветка UP: fact < 0.9×resolve
    TIGHTEN = "tighten"  # ветка DOWN: fact >= 0.9×resolve


@dataclass(frozen=True)
class CalibrationStepState:
    """Снимок adaptive step для следующего NORMAL-тика."""

    effective_steps: int
    direct: CalibrationDirect


def classify_calibration_direct(
    fact_pay_for_order: float | None,
    resolve: float,
) -> CalibrationDirect:
    """Ветка UP, если fact ниже 90% resolve; иначе ветка DOWN (``CalibrationDirect``)."""
    if fact_pay_for_order is None:
        return CalibrationDirect.TIGHTEN
    if float(fact_pay_for_order) < MAX_PAY_STABILIZATION_RATIO * float(resolve):
        return CalibrationDirect.LOOSEN
    return CalibrationDirect.TIGHTEN


def resolve_effective_calibration_steps(
    base_max: int,
    *,
    prev: CalibrationStepState | None,
    current_direct: CalibrationDirect,
) -> int:
    """Первый тик → 1; same direct ×2 (cap); flip direct ÷2 floor.

    Args:
        base_max: Cap из ``AdvSetting.keyword_calibration_max_step``.
        prev: Предыдущее состояние из Redis.
        current_direct: Направление текущего тика.

    Returns:
        Число effective ladder-шагов (UP или DOWN) на ключ за calibration.
    """
    cap = max(1, int(base_max))
    if prev is None:
        return 1
    if prev.direct == current_direct:
        return min(max(1, prev.effective_steps) * 2, cap)
    return max(max(1, prev.effective_steps) // 2, 1)
