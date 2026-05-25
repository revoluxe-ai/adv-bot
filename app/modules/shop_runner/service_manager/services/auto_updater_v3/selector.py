"""Select UP/DOWN actions from campaign state and per-keyword v3 context.

Signal matrix (v3):
- Plan/fact unchanged short-circuit in orchestrator.
- ``SalesStates`` from ``detect_campaign_state`` — global economy (OPTIMAL / UNDERPERFORM / …).
- Полочная фаза: ``rec_system_mode`` + авто ``started`` → ``plan_shelf_promotion_actions``
  (без 1–2–3 rollout). Иначе — ``RolloutPlanner`` + ``AdvSetting.aggressiveness``.

Сравнение ``organic_clicks`` vs ``shelf_clicks`` и стратегия MIN_CPO/MAX_CONV — только
``AdvStrategySelector`` / ``change_adv_strategy``, **не** в этом модуле.
``traffic_clicks_dto`` в orchestrator при полках — для UI/обогащения, не для ветвления UP здесь.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    keyword_has_proven_ad_stats,
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_rollout_down_one,
    plan_rollout_underperform_one,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.shelf_promotion_policy import (
    plan_shelf_promotion_actions,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)

@dataclass(frozen=True)
class KeywordV3Context:
    keyword: CalculatedKeyword
    position_profile: list[PositionProfilePoint] | None


def select_v3_actions(
    *,
    state: SalesStates,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    rollout_aggressiveness: int | None = None,
) -> list[V3Action]:
    """Return at most one mode change per cycle (see plan: single switch)."""
    prepared: list[tuple[KeywordV3Context, KeywordStrategyMode, bool]] = []
    for ctx in contexts:
        mode = stored_strategy_mode(ctx.keyword)
        proven = keyword_has_proven_ad_stats(ctx.keyword)
        prepared.append((ctx, mode, proven))

    if shelf_promotion_active:
        return plan_shelf_promotion_actions(prepared, state=state)

    aggr = normalize_v3_rollout_aggressiveness(rollout_aggressiveness)

    if state == SalesStates.OPTIMAL:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="optimal")]

    if state == SalesStates.OVERSPEND:
        return plan_rollout_down_one(prepared, reason="overspend")

    if state == SalesStates.UNDERPERFORM:
        return plan_rollout_underperform_one(prepared, aggr)

    if state == SalesStates.STABLE:
        return plan_rollout_down_one(prepared, reason="stable")

    return [V3Action(action=V3ActionType.DO_NOTHING, reason="unknown_state")]
