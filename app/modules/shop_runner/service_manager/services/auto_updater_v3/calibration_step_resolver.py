"""Adaptive effective steps для resolve calibration (×2/÷2 по направлению).

Калибровка — самостоятельный степ: одна ветка за тик (UP **или** DOWN), цель — CPA
кампании у **0.9×resolve** (``MAX_PAY_STABILIZATION_RATIO``).

- **LOOSEN** — ``fact < 0.9×resolve``: limited UP (нарастить расход);
- **TIGHTEN** — ``fact >= 0.9×resolve``: limited DOWN trim (снизить ``state_cost > resolve``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)


class CalibrationDirect(StrEnum):
    """Направление калибровки относительно пола ``0.9×resolve``."""

    LOOSEN = "loosen"  # fact ниже пола → UP
    TIGHTEN = "tighten"  # fact на/выше пола → DOWN trim


@dataclass(frozen=True)
class CalibrationStepState:
    """Снимок adaptive step для следующего NORMAL-тика."""

    effective_steps: int
    direct: CalibrationDirect


def classify_calibration_direct(
    fact_pay_for_order: float | None,
    resolve: float,
) -> CalibrationDirect:
    """``LOOSEN`` если fact ниже 90% resolve, иначе ``TIGHTEN``."""
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
