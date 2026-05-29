"""Режим кампании V3 на тике: отдельно от keyword data tier.

``CampaignMode.NOT_READY`` — ``detect_campaign_state`` вернул ``None`` (нет безопасного
решения по РK; это не «пауза РK»).

``CampaignMode.NO_DATA`` — ``SalesStates.NO_DATA`` (нет fact CPA).

``CampaignMode.NORMAL`` — полный V3 pipeline.
"""

from __future__ import annotations

from enum import Enum

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)


class CampaignMode(str, Enum):
    """Campaign-level режим V3 (не путать с ``KeywordDataTier``)."""

    NOT_READY = "campaign_not_ready"
    NO_DATA = "campaign_no_data"
    NORMAL = "campaign_normal"


def resolve_campaign_mode(state: SalesStates | None) -> CampaignMode:
    """Определить campaign-level режим по результату ``detect_campaign_state``."""
    if state is None:
        return CampaignMode.NOT_READY
    if state == SalesStates.NO_DATA:
        return CampaignMode.NO_DATA
    return CampaignMode.NORMAL


def allows_ladder_phases(mode: CampaignMode) -> bool:
    """COST_REALLOCATION / PROFITABLE_EXPANSION / MAX_CPA_GUARD / selector."""
    return mode == CampaignMode.NORMAL


def is_campaign_full_stop(mode: CampaignMode) -> bool:
    """``NOT_READY``: без keyword bootstrap, ladder, flush, target_place sync."""
    return mode == CampaignMode.NOT_READY
