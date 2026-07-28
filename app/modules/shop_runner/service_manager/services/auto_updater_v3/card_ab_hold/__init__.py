"""Режим A/B Hold карточки: durable mode, setup decision, Redis coordination.

Spec: ``card-ab-hold-mode``. Paid automation path для стабильного теста карточки
(ENTER/HOLD/EXIT) без остановки биддера. Ownership — proposed decision
``card-ab-hold-write-path-ownership``.
"""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
    is_ab_hold_structural_freeze,
    is_epoch_managed_ab_hold,
    normalize_card_ab_hold_mode,
    normalize_card_ab_hold_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    can_apply_card_ab_hold_mode_via_excel,
    filter_ab_hold_pipeline_candidates,
    filter_bidder_eligible_by_ab_hold,
    filter_structural_act_candidates,
    should_allow_bidder_on_ab_hold,
    should_allow_structural_act,
    should_run_ab_hold,
    should_run_ab_setup,
    should_schedule_ordinary_updater,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AB_HOLD_MIN_VIEWS,
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
    eligible_keyword_texts_for_confirm,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stats_enable_gate import (
    allows_ab_hold_enable_for_stats_state,
    build_ab_hold_enable_blocked_by_stats_message,
)

__all__ = [
    "AB_HOLD_MIN_VIEWS",
    "AbHoldSetupAction",
    "CardAbHoldMode",
    "CardAbHoldPhase",
    "allows_ab_hold_enable_for_stats_state",
    "build_ab_hold_enable_blocked_by_stats_message",
    "can_apply_card_ab_hold_mode_via_excel",
    "classify_ab_hold_setup_keyword",
    "eligible_keyword_texts_for_confirm",
    "filter_ab_hold_pipeline_candidates",
    "filter_bidder_eligible_by_ab_hold",
    "filter_structural_act_candidates",
    "is_ab_hold_structural_freeze",
    "is_epoch_managed_ab_hold",
    "normalize_card_ab_hold_mode",
    "normalize_card_ab_hold_phase",
    "should_allow_bidder_on_ab_hold",
    "should_allow_structural_act",
    "should_run_ab_hold",
    "should_run_ab_setup",
    "should_schedule_ordinary_updater",
]
