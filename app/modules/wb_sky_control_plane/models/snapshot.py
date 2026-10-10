"""Authoritative CampaignResourceSnapshot и classification."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wb_sky_control_plane.models.enums import (
    BidTypeAuthority,
    CampaignLegRole,
    CampaignTopology,
    MappingStatus,
    PaymentTypeAuthority,
    PlacementFlagAuthority,
    ProductMembershipAuthority,
    WbCampaignStatusAuthority,
)

_FROZEN = ConfigDict(frozen=True)


class PlacementAuthorityV1(BaseModel):
    """Strict normalized placements (missing → UNKNOWN, not false)."""

    search: PlacementFlagAuthority = PlacementFlagAuthority.UNKNOWN
    recommendations: PlacementFlagAuthority = PlacementFlagAuthority.UNKNOWN


class CampaignLegSnapshotV1(BaseModel):
    """Authoritative normalized WB leg."""

    model_config = _FROZEN

    wb_adv_id: int
    role: CampaignLegRole
    bid_type: BidTypeAuthority = BidTypeAuthority.UNKNOWN
    payment_type: PaymentTypeAuthority = PaymentTypeAuthority.UNKNOWN
    placements: PlacementAuthorityV1 = Field(default_factory=PlacementAuthorityV1)
    status: WbCampaignStatusAuthority = WbCampaignStatusAuthority.UNKNOWN
    product_membership: ProductMembershipAuthority = ProductMembershipAuthority.UNKNOWN
    nm_ids: list[int] = Field(default_factory=list)
    name: str | None = None


class LocalPolicyStateV1(BaseModel):
    """Read-only local policy projection from AdvSetting (planning authority)."""

    budget: dict[str, object] = Field(default_factory=dict)
    sales: dict[str, object] = Field(default_factory=dict)
    bid_control: dict[str, object] = Field(default_factory=dict)


class CampaignClassificationV1(BaseModel):
    """Classification from authoritative WB normalization (not legacy type 8/9)."""

    topology: CampaignTopology = CampaignTopology.UNKNOWN
    payment_type: PaymentTypeAuthority = PaymentTypeAuthority.UNKNOWN
    has_unknown_authoritative_fields: bool = False
    reason_codes: list[str] = Field(default_factory=list)


class CampaignResourceSnapshotV1(BaseModel):
    """Authoritative snapshot per cmp_* resource."""

    resource_id: str
    wb_cabinet_id: int
    adv_setting_id: int | None = None
    auto_leg: CampaignLegSnapshotV1 | None = None
    search_leg: CampaignLegSnapshotV1 | None = None
    product_nm_ids: list[int] = Field(default_factory=list)
    local_policy: LocalPolicyStateV1 = Field(default_factory=LocalPolicyStateV1)
    classification: CampaignClassificationV1 = Field(
        default_factory=CampaignClassificationV1
    )
    mapping_status: MappingStatus = MappingStatus.NOT_FOUND
    state_token: str | None = None
