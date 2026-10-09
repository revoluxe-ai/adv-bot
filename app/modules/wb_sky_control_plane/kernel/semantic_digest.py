"""semantic_digest sd1 for ChangeSetV1."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.modules.wb_sky_control_plane.kernel.canonical_json import canonical_sha256
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1

SEMANTIC_DIGEST_VERSION = "sd1"


def _operation_semantic_projection(operation: BaseModel) -> dict[str, object]:
    """Semantic operation projection: preserve order, operation_id, exclude audit reason."""
    data = operation.model_dump(mode="json", exclude={"reason"}, exclude_unset=True)
    return data


def _preconditions_projection(changeset: ChangeSetV1) -> dict[str, str]:
    """Per-resource semantic preconditions keyed by resource_id."""
    out: dict[str, str] = {}
    for operation in changeset.operations:
        if operation.preconditions is None:
            continue
        resource_id = operation.resource.resource_id
        token = operation.preconditions.state_token
        existing = out.get(resource_id)
        if existing is not None and existing != token:
            # Conflicting preconditions on same resource — include both for digest drift.
            out[resource_id] = f"{existing}|{token}"
        else:
            out[resource_id] = token
    return out


def build_semantic_projection(changeset: ChangeSetV1) -> dict[str, Any]:
    """Explicit versioned semantic projection for sd1."""
    preconditions = _preconditions_projection(changeset)
    projection: dict[str, Any] = {
        "version": SEMANTIC_DIGEST_VERSION,
        "scope": {
            "provider": changeset.scope.provider,
            "shop_id": changeset.scope.shop_id,
        },
        "operations": [
            _operation_semantic_projection(op) for op in changeset.operations
        ],
    }
    if preconditions:
        projection["preconditions"] = preconditions
    return projection


def compute_semantic_digest(changeset: ChangeSetV1) -> str:
    """sd1: canonical semantic projection excluding changeset_id and audit metadata."""
    return canonical_sha256(build_semantic_projection(changeset), prefix="sd1_")
