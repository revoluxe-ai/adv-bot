"""Select UP/DOWN actions from campaign state and per-keyword v3 context.

Контракт V3 (два входа):

1. **Production (orchestrator):** preamble (bootstrap, realloc, expansion,
   ``plan_max_cpa_guard`` при OVERSPEND) → ``select_v3_post_gate_actions`` (только полка).
   ``select_v3_actions`` с ``plan``/``fact`` **не** выполняет ladder/OVERSPEND.

2. **Legacy / тесты без plan/fact:** полный ``select_v3_actions`` — OVERSPEND через
   ``plan_overspend_actions``, UNDERPERFORM/STABLE через rollout planner.

При ``plan is not None and fact is not None``:

- ``NO_DATA`` → ``DO_NOTHING`` (``campaign_no_data_wait``);
- иначе → только ``select_v3_post_gate_actions`` (shelf cleanup).

``plan_max_pay_for_order`` на этом пути **игнорируется** (guard в orchestrator).
Для OVERSPEND вне orchestrator: ``plan=None``, ``fact=None``, задать
``plan_max_pay_for_order``.

``AdvSetting.strategy`` (MIN_CPO/MAX_CONV) — отдельный контур ``change_adv_strategy``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_overspend_actions,
    plan_rollout_down_one,
    plan_rollout_underperform_one,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.shelf_promotion_policy import (
    plan_shelf_promotion_actions,  # legacy wrapper
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
    plan_shelf_rec_false_cleanup_down,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KeywordV3Context:
    keyword: CalculatedKeyword
    position_profile: list[PositionProfilePoint] | None


def select_v3_post_gate_actions(
    *,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode | None = None,
) -> list[V3Action]:
    """Post-gate: shelf rec-false cleanup only (без M2/M3/FINAL_TUNING)."""
    if not shelf_promotion_active:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="post_gate_no_shelf")]
    prepared = build_prepared_from_contexts(contexts)
    click_mode = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
    cleanup = plan_shelf_rec_false_cleanup_down(prepared, click_mode=click_mode)
    if cleanup:
        return cleanup
    return [V3Action(action=V3ActionType.DO_NOTHING, reason="post_gate_no_actions")]


def _select_v3_actions_with_plan_fact(
    *,
    state: SalesStates,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode | None,
) -> list[V3Action]:
    """Ветка orchestrator post-gate: не ladder, не ``plan_overspend_actions``.

    OVERSPEND/UNDERPERFORM/STABLE/OPTIMAL с plan/fact обрабатываются в ``process_adv_v3``
    до вызова селектора (``plan_max_cpa_guard``, realloc, expansion, …).
    """
    if state == SalesStates.NO_DATA:
        return [
            V3Action(
                action=V3ActionType.DO_NOTHING,
                reason="campaign_no_data_wait",
            )
        ]
    if state != SalesStates.OPTIMAL:
        logger.debug(
            "select_v3_actions: state=%s with plan/fact — preamble в orchestrator, "
            "post-gate shelf only",
            state.name,
        )
    return select_v3_post_gate_actions(
        contexts=contexts,
        shelf_promotion_active=shelf_promotion_active,
        shelf_click_mode=shelf_click_mode,
    )


def select_v3_actions(
    *,
    state: SalesStates,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    rollout_aggressiveness: int | None = None,
    shelf_click_mode: ShelfClickMode | None = None,
    plan_max_pay_for_order: float | None = None,
    plan: PlanData | None = None,
    fact: FactData | None = None,
) -> list[V3Action]:
    """Legacy selector: ladder/OVERSPEND только **без** ``plan``/``fact``.

    Args:
        state: ``SalesStates`` кампании.
        contexts: ключи с CH-профилем.
        shelf_promotion_active: полка включена.
        rollout_aggressiveness: 1–3 для UNDERPERFORM (только без plan/fact).
        shelf_click_mode: режим кликов полки.
        plan_max_pay_for_order: max себес для ``plan_overspend_actions`` (только если
            ``plan`` и ``fact`` не переданы).
        plan: если задан вместе с ``fact`` — post-gate контур orchestrator (см. module
            docstring); ``plan_max_pay_for_order`` не используется.
        fact: см. ``plan``.

    Returns:
        Список ``V3Action`` для применения к ledger.
    """
    if plan is not None and fact is not None:
        return _select_v3_actions_with_plan_fact(
            state=state,
            contexts=contexts,
            shelf_promotion_active=shelf_promotion_active,
            shelf_click_mode=shelf_click_mode,
        )

    prepared = build_prepared_from_contexts(contexts)
    aggr = normalize_v3_rollout_aggressiveness(rollout_aggressiveness)

    if shelf_promotion_active:
        click_mode = (
            shelf_click_mode
            if shelf_click_mode is not None
            else ShelfClickMode.UNKNOWN
        )
        return plan_shelf_promotion_actions(
            prepared,
            state=state,
            click_mode=click_mode,
            rollout_aggressiveness=aggr,
            plan_max_pay_for_order=plan_max_pay_for_order,
        )

    if state == SalesStates.OPTIMAL:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="optimal")]

    if state == SalesStates.NO_DATA:
        return [
            V3Action(
                action=V3ActionType.DO_NOTHING,
                reason="campaign_no_data_wait",
            )
        ]

    if state == SalesStates.OVERSPEND:
        # Только без plan/fact; с plan/fact — MAX_CPA_GUARD в orchestrator.
        if plan_max_pay_for_order is not None:
            return plan_overspend_actions(
                prepared, max_pay_for_order=float(plan_max_pay_for_order)
            )
        return plan_rollout_down_one(prepared, reason="overspend")

    if state == SalesStates.UNDERPERFORM:
        return plan_rollout_underperform_one(prepared, aggr)

    if state == SalesStates.STABLE:
        return plan_rollout_down_one(prepared, reason="stable")

    return [V3Action(action=V3ActionType.DO_NOTHING, reason="unknown_state")]
