"""Итог прогона NORMAL preamble."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
)


@dataclass
class PreamblePipelineRunResult:
    """Итог preamble NORMAL через ``UpdatePipeline``."""

    update_context: UpdateContext
    contexts: list[KeywordV3Context]
    all_contexts: list[KeywordV3Context]
    prepared: PreparedList
    eligibility: dict[int, KeywordV3Eligibility]
    ladder_inputs: LadderInputs
    cap_down_count: int = 0
    validate_not_full_count: int = 0
    validate_count: int = 0
    raise_state_count: int = 0
    reset_over_max_cpo_count: int = 0
    passing_up_count: int = 0
    shelf_count: int = 0
    guard_count: int = 0
    realloc_count: int = 0
    enable_count: int = 0
    calibration_count: int = 0
    guard_applied: bool = False
    calibration_executed: bool = False
