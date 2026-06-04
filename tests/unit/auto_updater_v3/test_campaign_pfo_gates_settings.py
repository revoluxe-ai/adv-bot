"""Unit: env-пороги PFO preamble через settings_master."""

from __future__ import annotations

import pytest

from app.settings.settings_master import Settings


@pytest.mark.unit
def test_pfo_plan_headroom_ratio_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO", raising=False)
    monkeypatch.delenv("V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO", raising=False)
    s = Settings()
    assert s.V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO == 0.9
    assert s.V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO == 0.9


@pytest.mark.unit
def test_pfo_plan_headroom_ratio_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO", "0.85")
    monkeypatch.setenv("V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO", "0.95")
    s = Settings()
    assert s.V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO == 0.85
    assert s.V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO == 0.95
