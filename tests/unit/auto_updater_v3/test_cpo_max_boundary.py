"""Unit: SSOT strict max CPO boundaries."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    campaign_cpo_over_max,
    cmp_over_max,
    cmp_within_max,
    keyword_pfo_over_max,
    keyword_pfo_within_max,
    ladder_cpo_within_ceiling,
)


@pytest.mark.unit
def test_cmp_over_max_strict() -> None:
    assert cmp_over_max(121.0, 120.0) is True
    assert cmp_over_max(120.0, 120.0) is False
    assert cmp_over_max(119.0, 120.0) is False


@pytest.mark.unit
def test_cmp_within_max_strict() -> None:
    assert cmp_within_max(119.0, 120.0) is True
    assert cmp_within_max(120.0, 120.0) is False
    assert cmp_within_max(121.0, 120.0) is False


@pytest.mark.unit
def test_keyword_pfo_boundaries() -> None:
    assert keyword_pfo_within_max(100.0, 120.0) is True
    assert keyword_pfo_within_max(120.0, 120.0) is False
    assert keyword_pfo_over_max(120.0, 120.0) is False
    assert keyword_pfo_over_max(121.0, 120.0) is True
    assert keyword_pfo_within_max(None, 120.0) is False


@pytest.mark.unit
def test_ladder_cpo_within_ceiling() -> None:
    assert ladder_cpo_within_ceiling(119.0, 120.0) is True
    assert ladder_cpo_within_ceiling(120.0, 120.0) is False


@pytest.mark.unit
def test_campaign_cpo_over_max() -> None:
    assert campaign_cpo_over_max(150.0, 120.0) is True
    assert campaign_cpo_over_max(120.0, 120.0) is False
    assert campaign_cpo_over_max(None, 120.0) is False
