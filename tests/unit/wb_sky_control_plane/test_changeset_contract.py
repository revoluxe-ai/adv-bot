"""ChangeSetV1 canonical contract validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.wb_sky_control_plane.kernel.validate import validate_changeset
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    SetBudgetPolicyOperation,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus

pytestmark = pytest.mark.unit


def _op(**kwargs: object) -> SetBudgetPolicyOperation:
    defaults: dict[str, object] = {
        "operation_id": "op-1",
        "resource": CampaignResourceRef(resource_id="cmp_abc123"),
        "payload": BudgetPolicyPayload(auto_budget_daily_limit=100),
    }
    defaults.update(kwargs)
    return SetBudgetPolicyOperation(**defaults)  # type: ignore[arg-type]


def test_changeset_rejects_empty_operations() -> None:
    with pytest.raises(ValidationError, match="operations must be non-empty"):
        ChangeSetV1(
            changeset_id="cs-1",
            scope=LogicalScopeV1(shop_id="shop-a"),
            operations=[],
        )


def test_changeset_rejects_duplicate_operation_id() -> None:
    """Дубликат operation_id остаётся конвертом и отклоняется dry-run целиком."""
    changeset = ChangeSetV1(
        changeset_id="cs-1",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[
            _op(operation_id="dup"),
            _op(operation_id="dup"),
        ],
    )
    result = validate_changeset(changeset, {}, {})
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert any(error.code == "DUPLICATE_OPERATION_ID" for error in result.errors)


def test_changeset_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ChangeSetV1(
            changeset_id="cs-1",
            scope=LogicalScopeV1(shop_id="shop-a"),
            operations=[_op()],
            wb_cabinet_id=1,  # type: ignore[call-arg]
        )


def test_changeset_rejects_invalid_scope_shop_id() -> None:
    with pytest.raises(ValidationError, match="shop_id must be non-empty"):
        LogicalScopeV1(shop_id="   ")


def test_changeset_models_are_frozen() -> None:
    cs = ChangeSetV1(
        changeset_id="cs-1",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[_op()],
    )
    with pytest.raises(ValidationError):
        cs.changeset_id = "other"  # type: ignore[misc]
