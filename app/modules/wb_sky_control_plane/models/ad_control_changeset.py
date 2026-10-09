"""AdControlChangeSetV1 — bounded configured settings mutations (dry-run only)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
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


class AdControlPreconditionV1(BaseModel):
    """Optimistic concurrency для configured row."""

    model_config = _FROZEN_FORBID

    state_token: str

    @field_validator("state_token")
    @classmethod
    def _validate_token(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("state_token must be non-empty")
        return stripped


class ShopAdControlFeaturePayloadV1(BaseModel):
    """Shop slot mutation body."""

    model_config = _FROZEN_FORBID

    feature_id: AdControlFeatureId
    schema_version: int = 1
    activation: ShopFeatureActivation
    payload: dict[str, object] | None = None


class CampaignAdControlFeaturePayloadV1(BaseModel):
    """Campaign slot mutation body."""

    model_config = _FROZEN_FORBID

    feature_id: AdControlFeatureId
    schema_version: int = 1
    mode: AdControlFeatureMode
    payload: dict[str, object] | None = None


class _AdControlOperationBase(BaseModel):
    model_config = _FROZEN_FORBID

    operation_id: str
    reason: str | None = None
    preconditions: AdControlPreconditionV1

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


class SetCampaignAdControlFeatureOperation(_AdControlOperationBase):
    op: Literal["campaign.set_ad_control_feature"] = "campaign.set_ad_control_feature"
    resource: AdvertCampaignRefV1
    payload: CampaignAdControlFeaturePayloadV1


AdControlOperationV1 = Annotated[
    SetShopAdControlFeatureOperation | SetCampaignAdControlFeatureOperation,
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
