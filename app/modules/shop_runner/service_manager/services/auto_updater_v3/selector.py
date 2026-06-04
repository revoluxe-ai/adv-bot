"""Select post-gate actions и ``KeywordV3Context`` для V3 pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)


@dataclass(frozen=True)
class KeywordV3Context:
    """Контекст одного ключa для ladder/tick-report (CH profile + CalculatedKeyword)."""

    keyword: CalculatedKeyword
    position_profile: list[PositionProfilePoint] | None


def select_v3_post_gate_actions(
    *,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode | None = None,
    ladder_inputs: LadderInputs | None = None,
    policy: SelectionPolicy | None = None,
) -> list[V3Action]:
    """Post-gate stub: shelf cleanup в preamble; здесь только DO_NOTHING."""
    _ = contexts, shelf_promotion_active, shelf_click_mode, ladder_inputs, policy
    return [V3Action(action=V3ActionType.DO_NOTHING, reason="post_gate_preamble_only")]
