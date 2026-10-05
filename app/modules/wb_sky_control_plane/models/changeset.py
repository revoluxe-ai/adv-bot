"""ChangeSetV1 и typed bounded operations."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_FROZEN_FORBID = ConfigDict(frozen=True, extra="forbid")


class ChangeSetMetadataV1(BaseModel):
    """Audit/nonsemantic metadata (исключается из semantic_digest)."""

    model_config = _FROZEN_FORBID

    origin: str | None = None
    reason: str | None = None
    decision_id: str | None = None
    experiment_id: str | None = None


class LogicalScopeV1(BaseModel):
    """Canonical external scope: provider + shop_id (не wb_cabinet_id)."""

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


class CampaignResourceRef(BaseModel):
    """Ссылка на existing logical campaign resource через cmp_* id."""

    model_config = _FROZEN_FORBID

    resource_id: str

    @field_validator("resource_id")
    @classmethod
    def _validate_resource_id_prefix(cls, value: str) -> str:
        if not value.startswith("cmp_"):
            raise ValueError("resource_id must use cmp_ opaque prefix")
        return value


class OperationPreconditionV1(BaseModel):
    """Precondition на per-resource state_token."""

    model_config = _FROZEN_FORBID

    state_token: str


class BudgetPolicyPayload(BaseModel):
    """Bounded budget policy fields (AdvSetting authoritative subset)."""

    model_config = _FROZEN_FORBID

    auto_budget_watchdog_enabled: bool | None = None
    auto_budget_daily_limit: int | None = None
    search_auto_budget_daily_limit: int | None = None
    use_common_budget: bool | None = None
    common_budget_daily_limit: int | None = None
    auto_budget_total_limit: int | None = None
    search_auto_budget_total_limit: int | None = None
    common_budget_total_limit: int | None = None


class SalesPolicyPayload(BaseModel):
    """Bounded sales policy fields."""

    model_config = _FROZEN_FORBID

    orders_source_for_auto_mode: str | None = None
    plan_for_sales_for_day: int | None = None
    target_price_for_order: float | None = None
    max_price_for_order: int | None = None
    sales_predict_method: str | None = None
    strategy: str | None = None
    auto_update_strategy: bool | None = None


class BidControlPolicyPayload(BaseModel):
    """Bounded bid-control policy fields (auto_shelf module)."""

    model_config = _FROZEN_FORBID

    auto_shelf_bid_control_enabled: bool | None = None
    auto_shelf_bid_control_strategy: str | None = None


class _OperationBase(BaseModel):
    """Base fields shared by all canonical operations."""

    model_config = _FROZEN_FORBID

    operation_id: str
    resource: CampaignResourceRef
    reason: str | None = None
    preconditions: OperationPreconditionV1 | None = None

    @field_validator("operation_id")
    @classmethod
    def _validate_operation_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("operation_id must be non-empty")
        return stripped


class SetBudgetPolicyOperation(_OperationBase):
    op: Literal["campaign.set_budget_policy"] = "campaign.set_budget_policy"
    payload: BudgetPolicyPayload


class SetSalesPolicyOperation(_OperationBase):
    op: Literal["campaign.set_sales_policy"] = "campaign.set_sales_policy"
    payload: SalesPolicyPayload


class SetBidControlPolicyOperation(_OperationBase):
    op: Literal["campaign.set_bid_control_policy"] = "campaign.set_bid_control_policy"
    payload: BidControlPolicyPayload


CampaignOperationV1 = Annotated[
    SetBudgetPolicyOperation | SetSalesPolicyOperation | SetBidControlPolicyOperation,
    Field(discriminator="op"),
]


class ChangeSetV1(BaseModel):
    """Transport-independent ChangeSet (changeset_id — audit, не semantic)."""

    model_config = _FROZEN_FORBID

    contract_version: Literal["v1"] = "v1"
    changeset_id: str
    scope: LogicalScopeV1
    operations: list[CampaignOperationV1]
    metadata: ChangeSetMetadataV1 = Field(default_factory=ChangeSetMetadataV1)

    @model_validator(mode="after")
    def _validate_operations(self) -> ChangeSetV1:
        if not self.operations:
            raise ValueError("operations must be non-empty")
        operation_ids = [op.operation_id for op in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("duplicate operation_id")
        return self
