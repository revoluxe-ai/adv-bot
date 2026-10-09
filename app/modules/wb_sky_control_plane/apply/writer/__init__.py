"""Apply writer adapters (Slice C: PG policy only)."""

from app.modules.wb_sky_control_plane.apply.writer.pg_campaign_settings_policy_v1 import (
    apply_plan_to_adv_settings,
)

__all__ = ["apply_plan_to_adv_settings"]
