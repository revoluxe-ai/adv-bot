"""Regression: Excel MUST NOT apply A/B Hold mode (decision §9 / spec).

Spec ``card-ab-hold-mode``: no EDIT column; leftover import ignored;
``can_apply_card_ab_hold_mode_via_excel`` always False.
"""

from __future__ import annotations

import pytest

from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EDITABLE_ADV_SETTING_COLUMNS,
    EXCEL_TEMPLATE_VERSION,
    ordered_edit_fields,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    can_apply_card_ab_hold_mode_via_excel,
)


@pytest.mark.unit
def test_excel_schema_has_no_card_ab_hold_edit_column() -> None:
    """9.1/9.2: schema MUST NOT expose EDIT ``card_ab_hold_mode``."""
    assert "card_ab_hold_mode" not in EDITABLE_ADV_SETTING_COLUMNS
    assert "card_ab_hold_mode" not in ordered_edit_fields()
    assert EXCEL_TEMPLATE_VERSION >= 6


@pytest.mark.unit
@pytest.mark.parametrize(
    "requested_mode",
    [
        CardAbHoldMode.ACTIVE.value,
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.OFF.value,
        "active",
        "pending_setup",
        "off",
    ],
)
def test_excel_gate_always_denies_any_mode(requested_mode: str) -> None:
    """9.1: import applying any mode via excel gate is rejected (always False)."""
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=True,
            requested_mode=requested_mode,
            stats_fresh_enough=True,
        )
        is False
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=False,
            requested_mode=requested_mode,
            stats_fresh_enough=False,
        )
        is False
    )


@pytest.mark.unit
def test_import_apply_does_not_call_excel_ab_hold_gate_helpers() -> None:
    """9.3/9.4: apply_adv_excel_rows не вызывает Excel A/B Hold gate helpers."""
    from app.client_bot.user_interface.services.adv_excel_roundtrip import import_apply

    code = import_apply.apply_adv_excel_rows.__code__
    assert "can_apply_card_ab_hold_mode_via_excel" not in code.co_names
    assert "evaluate_ab_hold_enable_stats" not in code.co_names
