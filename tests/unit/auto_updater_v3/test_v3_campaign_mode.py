"""Unit: CampaignMode resolution."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
    allows_data_bootstrap,
    allows_ladder_phases,
    resolve_campaign_mode,
)


@pytest.mark.unit
def test_resolve_campaign_mode_not_ready() -> None:
    assert resolve_campaign_mode(None) == CampaignMode.NOT_READY
    assert not allows_data_bootstrap(CampaignMode.NOT_READY)
    assert not allows_ladder_phases(CampaignMode.NOT_READY)


@pytest.mark.unit
def test_resolve_campaign_mode_no_data() -> None:
    assert resolve_campaign_mode(SalesStates.NO_DATA) == CampaignMode.NO_DATA
    assert allows_data_bootstrap(CampaignMode.NO_DATA)
    assert not allows_ladder_phases(CampaignMode.NO_DATA)


@pytest.mark.unit
def test_resolve_campaign_mode_normal() -> None:
    assert resolve_campaign_mode(SalesStates.OPTIMAL) == CampaignMode.NORMAL
    assert allows_data_bootstrap(CampaignMode.NORMAL)
    assert allows_ladder_phases(CampaignMode.NORMAL)
