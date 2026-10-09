"""Deterministic intervention signature (primary retrieval identity)."""

from __future__ import annotations

from typing import Any

from app.modules.decision_experiment_memory.canonical_json import canonical_sha256
from app.modules.decision_experiment_memory.domain.plan import TreatmentDefinition


def build_intervention_signature_payload(
    treatment: TreatmentDefinition,
    *,
    changeset_semantic_digest: str | None = None,
    control_mode: str | None = None,
) -> dict[str, Any]:
    """Build canonical signature input (no free-text narrative)."""
    return {
        "setting_keys": list(treatment.setting_keys),
        "old_values": treatment.old_values,
        "new_values": treatment.new_values,
        "scope": {
            "shop_id": treatment.scope_shop_id,
            "cmp_ids": list(treatment.scope_cmp_ids),
            "nm_ids": list(treatment.scope_nm_ids),
        },
        "control_mode": control_mode,
        "changeset_semantic_digest": changeset_semantic_digest,
    }


def intervention_signature_digest(
    treatment: TreatmentDefinition,
    *,
    changeset_semantic_digest: str | None = None,
    control_mode: str | None = None,
) -> str:
    """Return deterministic digest for intervention similarity retrieval."""
    payload = build_intervention_signature_payload(
        treatment,
        changeset_semantic_digest=changeset_semantic_digest,
        control_mode=control_mode,
    )
    return canonical_sha256(payload)
