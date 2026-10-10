"""S20/S21 executable evidence — contract version and trust boundary."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import TransportChannel
from app.modules.wb_sky_control_plane.apply.models.context import (
    ApplyInvocationContext,
    PermissionGrantsV1,
    PrincipalRefV1,
    ShopAuthorizationV1,
)
from app.modules.wb_sky_control_plane.apply.models.request import ApplyRequestV1
from app.modules.wb_sky_control_plane.apply.validation import unsupported_contract_version
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    SetBudgetPolicyOperation,
)

pytestmark = pytest.mark.unit


def _minimal_changeset() -> ChangeSetV1:
    return ChangeSetV1(
        changeset_id="cs_test_1",
        scope=LogicalScopeV1(shop_id="shop_1"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-1",
                resource=CampaignResourceRef(resource_id="cmp_abc123"),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
            )
        ],
    )


def test_s20_unsupported_contract_version_fails_closed() -> None:
    request = ApplyRequestV1(
        contract_version="apply_v0",
        idempotency_key="k1",
        changeset=_minimal_changeset(),
        dry_run_receipt_id="rcpt_1",
    )
    reason = unsupported_contract_version(request)
    assert reason is not None

    supported = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key="k1",
        changeset=_minimal_changeset(),
        dry_run_receipt_id="rcpt_1",
    )
    assert unsupported_contract_version(supported) is None


def test_s21_apply_request_rejects_forged_auth_fields() -> None:
    base = {
        "contract_version": APPLY_CONTRACT_VERSION,
        "idempotency_key": "k1",
        "changeset": _minimal_changeset().model_dump(),
        "dry_run_receipt_id": "rcpt_1",
    }
    with pytest.raises(ValidationError):
        ApplyRequestV1.model_validate(
            {
                **base,
                "principal_ref": {"kind": "wb_user", "principal_id": "forged"},
            }
        )
    with pytest.raises(ValidationError):
        ApplyRequestV1.model_validate(
            {
                **base,
                "permission_grants": {"apply_campaign_settings": True},
            }
        )


def test_s21_invocation_context_is_distinct_trusted_type() -> None:
    ctx = ApplyInvocationContext(
        principal_ref=PrincipalRefV1(kind="wb_user", principal_id="u1"),
        shop_authorization=ShopAuthorizationV1(
            shop_id="shop_1", authorized=True
        ),
        permission_grants=PermissionGrantsV1(apply_campaign_settings=True),
        transport_channel=TransportChannel.API,
        auth_proof_ref="session:opaque",
    )
    assert ctx.is_authorized_for_shop("shop_1")
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key="k1",
        changeset=_minimal_changeset(),
        dry_run_receipt_id="rcpt_1",
    )
    assert not hasattr(request, "principal_ref")
