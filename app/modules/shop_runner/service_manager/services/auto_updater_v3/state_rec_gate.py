"""State-level полочный rec_gate для V3 лестницы M/O/C.

Сравнивает ``ModeCandidate.predicted_orders_per_view`` (к→з) с ``rec_orders_per_view``
(baseline полок). Key-level ``above_rec_conversion`` здесь не используется.
"""

from __future__ import annotations

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
REC_GATE_MARK_UNKNOWN_BASELINE = "Н"
REC_GATE_MARK_FAIL = ""


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


def passes_rec_gate_for_target_state(
    candidate: ModeCandidate,
    *,
    target_mode: KeywordStrategyMode,
    policy: SelectionPolicy,
    rec_orders_per_view: float | None,
    rk_orders_per_cart: float | None,
) -> bool:
    """State проходит полочный gate, если к→з state выше baseline полок.

    Args:
        candidate: ``ModeCandidate`` целевого state (M/O/C).
        target_mode: Целевой режим (для логов; gate по ``candidate``).
        policy: Политика тика (organic/shelf).
        rec_orders_per_view: Baseline заказы/показ полок; ``None`` — gate pass.
        rk_orders_per_cart: RK корз→заказ 7д для расчёта к→з.

    Returns:
        True если state разрешён с учётом полочного gate.
    """
    _ = target_mode
    if not _shelf_rec_policy_active(policy.click_mode):
        return True
    if rec_orders_per_view is None:
        return True
    state_opv = _state_orders_per_view(
        candidate, rk_orders_per_cart=rk_orders_per_cart
    )
    if state_opv is None:
        return False
    return state_opv > float(rec_orders_per_view)


def resolve_rec_gate_mark(
    candidate: ModeCandidate,
    *,
    policy: SelectionPolicy,
    rec_orders_per_view: float | None,
    rk_orders_per_cart: float | None,
) -> str:
    """Марка полочного gate для UI/debug: ``П`` / ``Н`` / пусто."""
    if not _shelf_rec_policy_active(policy.click_mode):
        return REC_GATE_MARK_FAIL
    if rec_orders_per_view is None:
        return REC_GATE_MARK_UNKNOWN_BASELINE
    if passes_rec_gate_for_target_state(
        candidate,
        target_mode=KeywordStrategyMode.MIN_CPA,
        policy=policy,
        rec_orders_per_view=rec_orders_per_view,
        rk_orders_per_cart=rk_orders_per_cart,
    ):
        return REC_GATE_MARK_PASS
    return REC_GATE_MARK_FAIL


def state_passes_rec_gate_for_mode(
    state_candidates_by_mode: dict[AggressionTargetMode, ModeCandidate],
    to_mode: KeywordStrategyMode,
    policy: SelectionPolicy,
    *,
    rec_orders_per_view: float | None,
    rk_orders_per_cart: float | None,
) -> bool:
    """Rec_gate для конкретного target mode по ``state_candidates_by_mode``."""
    mc = candidate_for_strategy_mode(to_mode, state_candidates_by_mode)
    if mc is None:
        return False
    return passes_rec_gate_for_target_state(
        mc,
        target_mode=to_mode,
        policy=policy,
        rec_orders_per_view=rec_orders_per_view,
        rk_orders_per_cart=rk_orders_per_cart,
    )
