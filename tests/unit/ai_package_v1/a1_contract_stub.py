"""Минимальный stub A1 CampaignResourceSnapshotV1 для contract non-aliasing tests.

Изолированный worktree не включает wb_sky_control_plane; stub повторяет
корневую форму control-plane контракта только для negative validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CampaignLegSnapshotV1Stub(BaseModel):
    """Упрощённая нога A1 snapshot (negative validation only)."""

    wb_adv_id: int | None = None


class CampaignResourceSnapshotV1Stub(BaseModel):
    """Stub A1 authoritative snapshot — MUST NOT validate AI Package payload."""

    resource_id: str
    wb_cabinet_id: int
    adv_setting_id: int | None = None
    auto_leg: CampaignLegSnapshotV1Stub | None = None
    search_leg: CampaignLegSnapshotV1Stub | None = None
    product_nm_ids: list[int] = Field(default_factory=list)
