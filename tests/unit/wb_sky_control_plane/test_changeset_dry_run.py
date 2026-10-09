"""Dry-run сценарии ChangeSetV1: validate_changeset без записи.

Каждый сценарий вызывает реальный ``validate_changeset`` и, где нужна
нормализация, реальный ``normalize_value`` через mutation policy.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import cast

import pytest

from app.modules.campaign_settings_contract import excel_editable_fields
from app.modules.wb_sky_control_plane.kernel.capabilities_eval import (
    evaluate_capabilities,
)
from app.modules.wb_sky_control_plane.kernel.domain_validators import (
    DOMAIN_VALIDATOR_IMPL,
)
from app.modules.wb_sky_control_plane.kernel.mutation_policy import (
    BID_CONTROL_FIELDS,
    BUDGET_FIELDS,
    SALES_FIELDS,
)
from app.modules.wb_sky_control_plane.kernel.validate import validate_changeset
from app.modules.wb_sky_control_plane.models.capabilities import CampaignCapabilitiesV1
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignOperationV1,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    OperationPreconditionV1,
    SalesPolicyPayload,
    SetBudgetPolicyOperation,
    SetSalesPolicyOperation,
    SetBidControlPolicyOperation,
    BidControlPolicyPayload,
)
from app.modules.wb_sky_control_plane.models.enums import (
    CampaignTopology,
    DryRunStatus,
    MappingStatus,
    PaymentTypeAuthority,
)
from app.modules.wb_sky_control_plane.models.plan import (
    ChangeSetValidationResult,
    PriorChangeSetRecord,
)
from app.modules.wb_sky_control_plane.models.snapshot import (
    CampaignClassificationV1,
    CampaignResourceSnapshotV1,
    LocalPolicyStateV1,
)

pytestmark = pytest.mark.unit

_RESOURCE = "cmp_abc123"
_TOKEN = "st1_generation"
_GRANTS = frozenset(
    {
        "campaign.set_budget_policy",
        "campaign.set_sales_policy",
        "campaign.set_bid_control_policy",
    }
)
_PACKAGE = Path(__file__).resolve().parents[3] / "app" / "modules" / "wb_sky_control_plane"
_FORBIDDEN_IMPORT_PREFIXES = (
    "app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2",
    "app.core.mp.wb.api.managers",
    "app.modules.shop_runner",
    "app.client_bot.user_interface.services.adv_excel_roundtrip",
)


def _classification(
    payment: PaymentTypeAuthority = PaymentTypeAuthority.CPM,
) -> CampaignClassificationV1:
    return CampaignClassificationV1(
        topology=CampaignTopology.AUTO_ONLY,
        payment_type=payment,
    )


def _snapshot(
    *,
    resource_id: str = _RESOURCE,
    token: str | None = _TOKEN,
    budget: dict[str, object] | None = None,
    sales: dict[str, object] | None = None,
    bid_control: dict[str, object] | None = None,
    mapping: MappingStatus = MappingStatus.OK,
    payment: PaymentTypeAuthority = PaymentTypeAuthority.CPM,
    adv_setting_id: int | None = 77,
) -> CampaignResourceSnapshotV1:
    return CampaignResourceSnapshotV1(
        resource_id=resource_id,
        wb_cabinet_id=1,
        adv_setting_id=adv_setting_id,
        state_token=token,
        mapping_status=mapping,
        classification=_classification(payment),
        local_policy=LocalPolicyStateV1(
            budget={"auto_budget_daily_limit": 10} if budget is None else budget,
            sales={} if sales is None else sales,
            bid_control={} if bid_control is None else bid_control,
        ),
    )


def _pre(
    token: str = _TOKEN,
    expected: dict[str, str | int | float | bool | None] | None = None,
) -> OperationPreconditionV1:
    return OperationPreconditionV1(
        state_token=token,
        expected_current_value=expected,
    )


def _budget(
    *,
    operation_id: str = "op-budget",
    resource_id: str = _RESOURCE,
    limit: int = 100,
    token: str | None = _TOKEN,
    expected: dict[str, str | int | float | bool | None] | None = None,
    omit_preconditions: bool = False,
) -> SetBudgetPolicyOperation:
    preconditions = None
    if not omit_preconditions and token is not None:
        preconditions = _pre(token, expected)
    return SetBudgetPolicyOperation(
        operation_id=operation_id,
        resource=CampaignResourceRef(resource_id=resource_id),
        payload=BudgetPolicyPayload(auto_budget_daily_limit=limit),
        preconditions=preconditions,
    )


def _changeset(
    operations: list[CampaignOperationV1],
    changeset_id: str = "cs-1",
) -> ChangeSetV1:
    return ChangeSetV1(
        changeset_id=changeset_id,
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=operations,
    )


def _run(
    changeset: ChangeSetV1,
    snapshots: dict[str, CampaignResourceSnapshotV1],
    *,
    prior: PriorChangeSetRecord | None = None,
    capability_grants: frozenset[str] | None = None,
    capabilities: dict[str, CampaignCapabilitiesV1] | None = None,
) -> ChangeSetValidationResult:
    caps = capabilities
    if caps is None:
        caps = {
            resource_id: evaluate_capabilities(snapshot)
            for resource_id, snapshot in snapshots.items()
        }
    return validate_changeset(
        changeset,
        snapshots,
        caps,
        prior=prior,
        capability_grants=capability_grants,
    )


def test_valid_bounded_operation_ok() -> None:
    """Совпадающий state_token и grant дают OK и semantic diff."""
    snapshot = _snapshot()
    result = _run(
        _changeset([_budget(limit=100)]),
        {_RESOURCE: snapshot},
        capability_grants=_GRANTS,
    )
    assert result.status == DryRunStatus.OK
    assert result.plan is not None
    assert len(result.diffs) == 1
    entry = result.diffs[0]
    assert entry.resource_id == _RESOURCE
    assert entry.old == 10
    assert entry.requested == 100
    assert entry.normalized == 100
    assert entry.field_path == f"{_RESOURCE}.budget.auto_budget_daily_limit"


def test_stale_state_token() -> None:
    result = _run(
        _changeset([_budget(token="stale-token")]),
        {_RESOURCE: _snapshot()},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "STATE_TOKEN_STALE"
    assert "stale or invalid generation token" in result.errors[0].message


def test_missing_state_token() -> None:
    omitted = _run(
        _changeset([_budget(omit_preconditions=True)]),
        {_RESOURCE: _snapshot()},
    )
    empty = _run(
        _changeset([_budget(token="")]),
        {_RESOURCE: _snapshot()},
    )
    assert omitted.status == DryRunStatus.REJECTED
    assert empty.status == DryRunStatus.REJECTED
    assert omitted.diffs == []
    assert empty.diffs == []
    assert omitted.errors[0].code == "STATE_TOKEN_MISSING"
    assert empty.errors[0].code == "STATE_TOKEN_MISSING"


def test_duplicate_changeset_id_conflict() -> None:
    snapshot = _snapshot()
    changeset = _changeset([_budget(limit=100)])
    prior = PriorChangeSetRecord(
        changeset_id=changeset.changeset_id,
        canonical_hash="sd1_different_body",
        status=DryRunStatus.OK,
    )
    result = _run(changeset, {_RESOURCE: snapshot}, prior=prior)
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.plan is None
    assert result.errors[0].code == "CHANGESET_ID_CONFLICT"


def test_duplicate_changeset_id_replay() -> None:
    """Тот же id и hash воспроизводят OK и NO_OP, не записывая prior."""
    ok_snapshot = _snapshot()
    ok_changeset = _changeset([_budget(limit=100)])
    first_ok = _run(ok_changeset, {_RESOURCE: ok_snapshot})
    ok_prior_before = {
        "changeset_id": ok_changeset.changeset_id,
        "canonical_hash": first_ok.semantic_digest,
        "status": first_ok.status,
    }
    ok_prior = PriorChangeSetRecord(
        changeset_id=ok_changeset.changeset_id,
        canonical_hash=first_ok.semantic_digest,
        status=first_ok.status,
    )
    replay_ok = _run(ok_changeset, {_RESOURCE: ok_snapshot}, prior=ok_prior)
    replay_ok_again = _run(ok_changeset, {_RESOURCE: ok_snapshot}, prior=ok_prior)
    assert first_ok.status == DryRunStatus.OK
    assert replay_ok.status == ok_prior.status
    assert replay_ok.model_dump() == replay_ok_again.model_dump()
    assert ok_prior.model_dump() == ok_prior_before

    noop_snapshot = _snapshot(budget={"auto_budget_daily_limit": 100})
    noop_changeset = _changeset([_budget(limit=100)], changeset_id="cs-noop")
    first_noop = _run(noop_changeset, {_RESOURCE: noop_snapshot})
    noop_prior = PriorChangeSetRecord(
        changeset_id=noop_changeset.changeset_id,
        canonical_hash=first_noop.semantic_digest,
        status=first_noop.status,
    )
    replay_noop = _run(noop_changeset, {_RESOURCE: noop_snapshot}, prior=noop_prior)
    assert first_noop.status == DryRunStatus.NO_OP
    assert replay_noop.status == DryRunStatus.NO_OP
    assert replay_noop.model_dump() == first_noop.model_dump()


def test_cmp_resource_identity() -> None:
    result = _run(
        _changeset([_budget(limit=100)]),
        {_RESOURCE: _snapshot(adv_setting_id=77)},
    )
    assert result.status == DryRunStatus.OK
    entry = result.diffs[0]
    assert entry.resource_id == _RESOURCE
    assert entry.field_path.startswith(f"{_RESOURCE}.")
    dumped = entry.model_dump()
    assert "leg_role" not in dumped
    assert "adv_setting_id" not in entry.field_path
    assert "77" not in entry.field_path


def test_unresolved_resource_ref() -> None:
    result = _run(_changeset([_budget()]), {})
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "RESOURCE_SNAPSHOT_MISSING"


def test_duplicate_operation_id() -> None:
    result = _run(
        _changeset(
            [
                _budget(operation_id="dup", limit=100),
                _budget(operation_id="dup", limit=200),
            ]
        ),
        {_RESOURCE: _snapshot()},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "DUPLICATE_OPERATION_ID"


def test_unsupported_mutation() -> None:
    """Операция вне bounded-набора отклоняется, даже если конверт собран в обход."""
    operation = SetBudgetPolicyOperation.model_construct(
        operation_id="op-unknown",
        op=cast(object, "campaign.unsupported"),
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
        preconditions=_pre(),
    )
    changeset = ChangeSetV1.model_construct(
        contract_version="v1",
        changeset_id="cs-unsupported",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[operation],
    )
    result = _run(changeset, {_RESOURCE: _snapshot()})
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "UNSUPPORTED_OPERATION"


def test_invalid_value() -> None:
    operation = SetSalesPolicyOperation(
        operation_id="op-sales",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=SalesPolicyPayload(orders_source_for_auto_mode="NOT_A_SOURCE"),
        preconditions=_pre(),
    )
    result = _run(_changeset([operation]), {_RESOURCE: _snapshot()})
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "INVALID_VALUE"


def test_unknown_capability() -> None:
    result = _run(
        _changeset([_budget(limit=100)]),
        {_RESOURCE: _snapshot()},
        capability_grants=frozenset(
            {"campaign.set_budget_policy", "campaign.not_in_catalog"}
        ),
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert any(error.code == "UNKNOWN_CAPABILITY" for error in result.errors)


def test_unsupported_capability() -> None:
    snapshot = _snapshot(payment=PaymentTypeAuthority.CPC)
    result = _run(_changeset([_budget(limit=100)]), {_RESOURCE: snapshot})
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "CAPABILITY_NOT_ELIGIBLE"
    assert result.errors[0].details["reason_code"] == "UNSUPPORTED_PAYMENT_TYPE"


def test_normalization() -> None:
    operation = SetSalesPolicyOperation(
        operation_id="op-sales",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=SalesPolicyPayload(target_price_for_order=10),
        preconditions=_pre(),
    )
    result = _run(
        _changeset([operation]),
        {_RESOURCE: _snapshot(sales={"target_price_for_order": 1.0})},
    )
    assert result.status == DryRunStatus.OK
    entry = result.diffs[0]
    assert entry.requested == 10
    assert isinstance(entry.requested, int)
    assert entry.normalized == 10.0
    assert entry.old == 1.0


def test_no_op() -> None:
    result = _run(
        _changeset([_budget(limit=10)]),
        {_RESOURCE: _snapshot(budget={"auto_budget_daily_limit": 10})},
    )
    assert result.status == DryRunStatus.NO_OP
    assert result.diffs == []
    assert result.plan is not None
    assert result.plan.is_no_op is True


def test_deterministic_diff() -> None:
    changeset = _changeset([_budget(limit=100)])
    snapshots = {_RESOURCE: _snapshot()}
    first = _run(changeset, snapshots, capability_grants=_GRANTS)
    second = _run(changeset, snapshots, capability_grants=_GRANTS)
    assert first.model_dump() == second.model_dump()
    assert first.status == DryRunStatus.OK


def test_expected_current_mismatch() -> None:
    result = _run(
        _changeset(
            [
                _budget(
                    limit=100,
                    expected={"auto_budget_daily_limit": 9},
                )
            ]
        ),
        {_RESOURCE: _snapshot(budget={"auto_budget_daily_limit": 10})},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "EXPECTED_CURRENT_VALUE_MISMATCH"


def test_omit_expected_does_not_bypass_token() -> None:
    result = _run(
        _changeset([_budget(token="not-the-generation")]),
        {_RESOURCE: _snapshot()},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "STATE_TOKEN_STALE"


def test_multiple_operations_ok() -> None:
    sales = SetSalesPolicyOperation(
        operation_id="op-sales",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=SalesPolicyPayload(plan_for_sales_for_day=5),
        preconditions=_pre(),
    )
    result = _run(
        _changeset([_budget(limit=100), sales]),
        {_RESOURCE: _snapshot(sales={"plan_for_sales_for_day": 1})},
    )
    assert result.status == DryRunStatus.OK
    assert len(result.diffs) == 2
    assert {entry.field_path for entry in result.diffs} == {
        f"{_RESOURCE}.budget.auto_budget_daily_limit",
        f"{_RESOURCE}.sales.plan_for_sales_for_day",
    }


def test_mixed_operations_atomic_reject() -> None:
    invalid = SetSalesPolicyOperation(
        operation_id="op-sales",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=SalesPolicyPayload(orders_source_for_auto_mode="NOT_A_SOURCE"),
        preconditions=_pre(),
    )
    result = _run(
        _changeset([_budget(limit=100), invalid]),
        {_RESOURCE: _snapshot()},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.plan is None
    assert any(error.code == "INVALID_VALUE" for error in result.errors)


def test_duplicate_target_mutation() -> None:
    result = _run(
        _changeset(
            [
                _budget(operation_id="op-a", limit=100),
                _budget(operation_id="op-b", limit=200),
            ]
        ),
        {_RESOURCE: _snapshot()},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert any(error.code == "DUPLICATE_TARGET" for error in result.errors)


def test_no_production_write() -> None:
    """OK, NO_OP и REJECTED не импортируют и не вызывают writer-адаптеры."""
    modules = (
        _PACKAGE / "kernel" / "validate.py",
        _PACKAGE / "kernel" / "mutation_policy.py",
        _PACKAGE / "kernel" / "domain_validators.py",
    )
    imported: set[str] = set()
    for path in modules:
        source = path.read_text(encoding="utf-8")
        assert "apply_adv_excel_rows" not in source
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
    for prefix in _FORBIDDEN_IMPORT_PREFIXES:
        assert not any(name.startswith(prefix) for name in imported)

    ok = _run(_changeset([_budget(limit=100)]), {_RESOURCE: _snapshot()})
    noop = _run(
        _changeset([_budget(limit=10)]),
        {_RESOURCE: _snapshot(budget={"auto_budget_daily_limit": 10})},
    )
    rejected = _run(_changeset([_budget(token="stale")]), {_RESOURCE: _snapshot()})
    assert ok.status == DryRunStatus.OK
    assert noop.status == DryRunStatus.NO_OP
    assert rejected.status == DryRunStatus.REJECTED


def test_unknown_mapping_rejects() -> None:
    result = _run(
        _changeset([_budget(limit=100)]),
        {_RESOURCE: _snapshot(mapping=MappingStatus.BROKEN)},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.errors[0].code == "MAPPING_NOT_OK"


def test_unknown_field_rejects() -> None:
    result = _run(
        _changeset(
            [_budget(limit=100, expected={"not_a_registered_field": 1})]
        ),
        {_RESOURCE: _snapshot()},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert any(error.code == "UNKNOWN_FIELD" for error in result.errors)


def test_domain_invariant_rejects() -> None:
    operation = SetSalesPolicyOperation(
        operation_id="op-sales",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=SalesPolicyPayload(
            target_price_for_order=50,
            max_price_for_order=10,
        ),
        preconditions=_pre(),
    )
    result = _run(_changeset([operation]), {_RESOURCE: _snapshot()})
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert any(error.code == "DOMAIN_INVARIANT" for error in result.errors)


def test_unimplemented_domain_validator_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(DOMAIN_VALIDATOR_IMPL, "non_negative_limits")
    result = _run(
        _changeset([_budget(limit=100)]),
        {_RESOURCE: _snapshot()},
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert result.plan is None
    assert any(
        error.code == "DOMAIN_VALIDATOR_UNIMPLEMENTED" for error in result.errors
    )


def test_excel_editable_does_not_grant_mutability() -> None:
    editable = excel_editable_fields("AdvSetting")
    assert "bot_active" in editable
    mutable = set(BUDGET_FIELDS) | set(SALES_FIELDS) | set(BID_CONTROL_FIELDS)
    assert "bot_active" not in mutable


def test_bid_control_policy_ok_via_validate_pipeline() -> None:
    """E2E validate_changeset: campaign.set_bid_control_policy → OK."""
    operation = SetBidControlPolicyOperation(
        operation_id="op-bid-ok",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=BidControlPolicyPayload(
            auto_shelf_bid_control_enabled=True,
            auto_shelf_bid_control_strategy="plan_distance",
        ),
        preconditions=_pre(),
    )
    snapshot = _snapshot(
        bid_control={
            "auto_shelf_bid_control_enabled": False,
            "auto_shelf_bid_control_strategy": None,
        }
    )
    result = _run(
        _changeset([operation]),
        {_RESOURCE: snapshot},
        capability_grants=_GRANTS,
    )
    assert result.status == DryRunStatus.OK
    assert len(result.diffs) >= 1
    paths = {entry.field_path for entry in result.diffs}
    assert f"{_RESOURCE}.bid_control.auto_shelf_bid_control_enabled" in paths


def test_bid_control_policy_no_op_via_validate_pipeline() -> None:
    operation = SetBidControlPolicyOperation(
        operation_id="op-bid-noop",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=BidControlPolicyPayload(auto_shelf_bid_control_enabled=True),
        preconditions=_pre(),
    )
    snapshot = _snapshot(
        bid_control={
            "auto_shelf_bid_control_enabled": True,
            "auto_shelf_bid_control_strategy": "plan_distance",
        }
    )
    result = _run(_changeset([operation]), {_RESOURCE: snapshot})
    assert result.status == DryRunStatus.NO_OP
    assert result.diffs == []


def test_bid_control_policy_rejected_requires_strategy_invariant() -> None:
    """REJECTED: enabled без стратегии в том же поколении (domain validator)."""
    operation = SetBidControlPolicyOperation(
        operation_id="op-bid-bad",
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=BidControlPolicyPayload(auto_shelf_bid_control_enabled=True),
        preconditions=_pre(),
    )
    snapshot = _snapshot(
        bid_control={
            "auto_shelf_bid_control_enabled": False,
            "auto_shelf_bid_control_strategy": None,
        }
    )
    result = _run(_changeset([operation]), {_RESOURCE: snapshot})
    assert result.status == DryRunStatus.REJECTED
    assert result.diffs == []
    assert any(
        error.code == "DOMAIN_INVARIANT"
        and error.details.get("validator") == "bid_control_enabled_requires_strategy"
        for error in result.errors
    )
