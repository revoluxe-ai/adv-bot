"""AdControlChangeSetV1 — bounded configured settings mutations (dry-run only)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    ShopFeatureActivation,
)

_FROZEN_FORBID = ConfigDict(frozen=True, extra="forbid")


class AdControlChangeSetMetadataV1(BaseModel):
    """Audit metadata (non-semantic)."""

    model_config = _FROZEN_FORBID

    origin: str | None = None
    reason: str | None = None


class AdControlLogicalScopeV1(BaseModel):
    """Shop scope for ad control mutations."""

    model_config = _FROZEN_FORBID

    provider: Literal["wildberries"] = "wildberries"
    shop_id: str

    @field_validator("shop_id")
    @classmethod
    def _validate_shop_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("shop_id must be non-empty")
        return stripped


class AdvertCampaignRefV1(BaseModel):
    """Campaign authority ``(shop_id, advert_id)`` — не ``main_nmid``."""

    model_config = _FROZEN_FORBID

    shop_id: str
    advert_id: int

    @field_validator("shop_id")
    @classmethod
    def _validate_shop_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("shop_id must be non-empty")
        return stripped

    @field_validator("advert_id")
    @classmethod
    def _validate_advert_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("advert_id must be positive")
        return value


class AdControlRevisionPreconditionV1(BaseModel):
    """
    CAS precondition for authoritative row.

    ``expected_revision=None`` => slot must be absent (create / idempotent clear).
    ``expected_revision=int`` => row must exist with that monotonic revision.
    """

    model_config = _FROZEN_FORBID

    expected_revision: int | None = None

    @field_validator("expected_revision")
    @classmethod
    def _validate_revision(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("expected_revision must be >= 1 when present")
        return value


class ShopAdControlFeaturePayloadV1(BaseModel):
    """Shop slot mutation body (ENABLED or explicit DISABLED)."""

    model_config = _FROZEN_FORBID

    feature_id: AdControlFeatureId
    schema_version: int = 1
    activation: ShopFeatureActivation
    payload: dict[str, object] | None = None


class CampaignFeatureTargetV1(BaseModel):
    """Campaign feature target without mode (disable / clear)."""

    model_config = _FROZEN_FORBID

    feature_id: AdControlFeatureId
    schema_version: int = 1


class CampaignOverridePayloadV1(BaseModel):
    """Campaign OVERRIDE body (INHERIT is never persisted)."""

    model_config = _FROZEN_FORBID

    feature_id: AdControlFeatureId
    schema_version: int = 1
    payload: dict[str, object]


class _AdControlOperationBase(BaseModel):
    model_config = _FROZEN_FORBID

    operation_id: str
    reason: str | None = None
    preconditions: AdControlRevisionPreconditionV1

    @field_validator("operation_id")
    @classmethod
    def _validate_operation_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("operation_id must be non-empty")
        return stripped


class SetShopAdControlFeatureOperation(_AdControlOperationBase):
    op: Literal["shop.set_ad_control_feature"] = "shop.set_ad_control_feature"
    payload: ShopAdControlFeaturePayloadV1


class SetCampaignAdControlOverrideOperation(_AdControlOperationBase):
    op: Literal["campaign.set_ad_control_override"] = "campaign.set_ad_control_override"
    resource: AdvertCampaignRefV1
    payload: CampaignOverridePayloadV1


class DisableCampaignAdControlFeatureOperation(_AdControlOperationBase):
    op: Literal["campaign.disable_ad_control_feature"] = (
        "campaign.disable_ad_control_feature"
    )
    resource: AdvertCampaignRefV1
    payload: CampaignFeatureTargetV1


class ClearCampaignAdControlFeatureOperation(_AdControlOperationBase):
    op: Literal["campaign.clear_ad_control_feature"] = "campaign.clear_ad_control_feature"
    resource: AdvertCampaignRefV1
    payload: CampaignFeatureTargetV1


AdControlOperationV1 = Annotated[
    SetShopAdControlFeatureOperation
    | SetCampaignAdControlOverrideOperation
    | DisableCampaignAdControlFeatureOperation
    | ClearCampaignAdControlFeatureOperation,
    Field(discriminator="op"),
]


class AdControlChangeSetV1(BaseModel):
    """Transport-independent ad control ChangeSet (no WB / PG writes in validator)."""

    model_config = _FROZEN_FORBID

    contract_version: Literal["v1"] = "v1"
    changeset_id: str
    scope: AdControlLogicalScopeV1
    operations: list[AdControlOperationV1]
    metadata: AdControlChangeSetMetadataV1 = Field(
        default_factory=AdControlChangeSetMetadataV1
    )

    @model_validator(mode="after")
    def _non_empty_ops(self) -> AdControlChangeSetV1:
        if not self.operations:
            raise ValueError("operations must be non-empty")
        return self
