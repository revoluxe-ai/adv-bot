"""State-level полочный rec_gate для V3 лестницы M/O/C.

Сравнивает ``ModeCandidate.predicted_orders_per_view`` (к→з) с ``rec_orders_per_view``
(baseline полок). Key-level ``above_rec_conversion`` здесь не используется.

Статусы:
- ``INACTIVE`` — gate не применяется (organic или ``rec_orders_per_view is None``);
- ``PASS`` — к→з state строго выше baseline;
- ``UNKNOWN`` — baseline есть, но к→з state неизвестен (нет RK или OPV);
- ``FAIL`` — к→з известен и не выше baseline.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    candidate_for_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    conv_views_to_orders_at_ch_point,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
    )

REC_GATE_MARK_PASS = "П"
REC_GATE_MARK_UNKNOWN = "Н"
REC_GATE_MARK_FAIL = ""

# Обратная совместимость имён в тестах/UI
REC_GATE_MARK_UNKNOWN_BASELINE = REC_GATE_MARK_UNKNOWN


class RecGateStatus(str, Enum):
    """Результат state-level rec gate для одного target state."""

    INACTIVE = "inactive"
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


def _shelf_rec_policy_active(click_mode: ShelfClickMode) -> bool:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        shelf_rec_conversion_policy_active,
    )

    return shelf_rec_conversion_policy_active(click_mode)


def _state_orders_per_view(
    candidate: ModeCandidate,
    *,
    rk_orders_per_cart: float | None,
) -> float | None:
    if candidate.predicted_orders_per_view is not None:
        return candidate.predicted_orders_per_view
    return conv_views_to_orders_at_ch_point(
        conv_carts_to_views=candidate.predicted_conversion,
        rk_orders_per_cart=rk_orders_per_cart,
    )


def resolve_rec_gate_status_for_target_state(
    candidate: ModeCandidate,
    *,
    target_mode: KeywordStrategyMode,
    policy: SelectionPolicy,
    rec_orders_per_view: float | None,
    rk_orders_per_cart: float | None,
) -> RecGateStatus:
    """Вычислить статус rec gate для целевого state M/O/C.

    Args:
        candidate: ``ModeCandidate`` целевого state.
        target_mode: Целевой режим (для логов; gate по ``candidate``).
        policy: Политика тика (organic/shelf).
        rec_orders_per_view: Baseline заказы/показ полок.
        rk_orders_per_cart: RK корз→заказ 7д для расчёта к→з.

    Returns:
        ``RecGateStatus`` для state.
    """
    _ = target_mode
    if not _shelf_rec_policy_active(policy.click_mode):
        return RecGateStatus.INACTIVE
    if rec_orders_per_view is None:
        return RecGateStatus.INACTIVE
    if rk_orders_per_cart is None:
        return RecGateStatus.UNKNOWN
    state_opv = _state_orders_per_view(
        candidate, rk_orders_per_cart=rk_orders_per_cart
    )
    if state_opv is None:
        return RecGateStatus.UNKNOWN
    if state_opv > float(rec_orders_per_view):
        return RecGateStatus.PASS
    return RecGateStatus.FAIL


def rec_gate_allows_up(status: RecGateStatus) -> bool:
    """UP / expansion разрешён при PASS, UNKNOWN и INACTIVE; FAIL блокирует."""
    return status in (
        RecGateStatus.INACTIVE,
        RecGateStatus.PASS,
        RecGateStatus.UNKNOWN,
    )


def rec_gate_triggers_cleanup(status: RecGateStatus) -> bool:
    """Cleanup/DOWN/FORCE_OFF только при явном FAIL текущего state."""
    return status == RecGateStatus.FAIL


def resolve_rec_gate_mark(
    candidate: ModeCandidate,
    *,
    policy: SelectionPolicy,
    rec_orders_per_view: float | None,
    rk_orders_per_cart: float | None,
) -> str:
    """Марка полочного gate для UI: ``П`` / ``Н`` / пусто."""
    status = resolve_rec_gate_status_for_target_state(
        candidate,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=policy,
        rec_orders_per_view=rec_orders_per_view,
        rk_orders_per_cart=rk_orders_per_cart,
    )
    if status == RecGateStatus.PASS:
        return REC_GATE_MARK_PASS
    if status == RecGateStatus.UNKNOWN:
        return REC_GATE_MARK_UNKNOWN
    return REC_GATE_MARK_FAIL


def state_rec_gate_status_for_mode(
    state_candidates_by_mode: dict[AggressionTargetMode, ModeCandidate],
    to_mode: KeywordStrategyMode,
    policy: SelectionPolicy,
    *,
    rec_orders_per_view: float | None,
    rk_orders_per_cart: float | None,
) -> RecGateStatus:
    """Rec_gate status для конкретного target mode по ``state_candidates_by_mode``."""
    mc = candidate_for_strategy_mode(to_mode, state_candidates_by_mode)
    if mc is None:
        return RecGateStatus.FAIL
    return resolve_rec_gate_status_for_target_state(
        mc,
        target_mode=to_mode,
        policy=policy,
        rec_orders_per_view=rec_orders_per_view,
        rk_orders_per_cart=rk_orders_per_cart,
    )
