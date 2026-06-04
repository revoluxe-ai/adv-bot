"""Unit: post-gate stub после preamble (NO_DATA обрабатывается в orchestrator)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    select_v3_post_gate_actions,
)


@pytest.mark.unit
def test_post_gate_stub_after_preamble() -> None:
    """Production post-gate: только DO_NOTHING (ladder в preamble)."""
    actions = select_v3_post_gate_actions(
        contexts=[],
        shelf_promotion_active=False,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DO_NOTHING
    assert actions[0].reason == "post_gate_preamble_only"
