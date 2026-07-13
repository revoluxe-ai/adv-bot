"""Режим A/B Hold карточки: durable mode, setup decision, Redis coordination.

Spec: ``card-ab-hold-mode``. Paid automation path для стабильного теста карточки
(ENTER/HOLD/EXIT) без остановки биддера. Ownership — proposed decision
``card-ab-hold-write-path-ownership``.
"""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
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
)

__all__ = [
    "AB_HOLD_MIN_VIEWS",
    "AbHoldSetupAction",
    "CardAbHoldMode",
    "classify_ab_hold_setup_keyword",
    "is_ab_hold_structural_freeze",
    "normalize_card_ab_hold_mode",
    "should_allow_bidder_on_ab_hold",
    "should_allow_structural_act",
    "should_run_ab_hold",
    "should_run_ab_setup",
    "should_schedule_ordinary_updater",
]
