"""Deterministic per-resource state_token st1 with operation-kind dependency profiles."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.kernel.canonical_json import canonical_sha256
from app.modules.wb_sky_control_plane.models.enums import CanonicalOperationKind
from app.modules.wb_sky_control_plane.models.snapshot import (
    CampaignLegSnapshotV1,
    CampaignResourceSnapshotV1,
)

STATE_TOKEN_VERSION = "st1"

_OP_POLICY_KEYS: dict[str, str] = {
    CanonicalOperationKind.SET_BUDGET_POLICY.value: "budget",
    CanonicalOperationKind.SET_SALES_POLICY.value: "sales",
    CanonicalOperationKind.SET_BID_CONTROL_POLICY.value: "bid_control",
}


def _leg_projection(leg: CampaignLegSnapshotV1 | None) -> dict[str, object] | None:
    if leg is None:
        return None
    return {
        "wb_adv_id": leg.wb_adv_id,
        "role": leg.role.value,
        "bid_type": leg.bid_type.value,
        "payment_type": leg.payment_type.value,
        "placements": {
            "search": leg.placements.search.value,
            "recommendations": leg.placements.recommendations.value,
        },
        "status": leg.status.value,
        "product_membership": leg.product_membership.value,
        "nm_ids": leg.nm_ids,
    }


def _policy_projection(
    snapshot: CampaignResourceSnapshotV1,
    *,
    target_op_kinds: frozenset[str],
) -> dict[str, object]:
    """Include only policy subtrees relevant to targeted operation kinds."""
    local = snapshot.local_policy
    out: dict[str, object] = {}
    for op_kind in target_op_kinds:
        key = _OP_POLICY_KEYS.get(op_kind)
        if key == "budget":
            out["budget"] = local.budget
        elif key == "sales":
            out["sales"] = local.sales
        elif key == "bid_control":
            out["bid_control"] = local.bid_control
    return out


def build_state_projection(
    snapshot: CampaignResourceSnapshotV1,
    *,
    target_op_kinds: frozenset[str] | None = None,
) -> dict[str, object]:
    """Explicit versioned state projection for st1."""
    ops = target_op_kinds if target_op_kinds is not None else frozenset(_OP_POLICY_KEYS)
    projection: dict[str, object] = {
        "version": STATE_TOKEN_VERSION,
        "resource_id": snapshot.resource_id,
        "wb_cabinet_id": snapshot.wb_cabinet_id,
        "auto_leg": _leg_projection(snapshot.auto_leg),
        "search_leg": _leg_projection(snapshot.search_leg),
        "product_nm_ids": snapshot.product_nm_ids,
        "classification": {
            "topology": snapshot.classification.topology.value,
            "payment_type": snapshot.classification.payment_type.value,
        },
    }
    policy = _policy_projection(snapshot, target_op_kinds=ops)
    if policy:
        projection["local_policy"] = policy
    return projection


def compute_state_token(
    snapshot: CampaignResourceSnapshotV1,
    *,
    target_op_kinds: frozenset[str] | None = None,
) -> str:
    """st1: union of dependency profiles for operations targeting this resource."""
    projection = build_state_projection(snapshot, target_op_kinds=target_op_kinds)
    return canonical_sha256(projection, prefix="st1_")
