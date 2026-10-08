"""pd1 — deterministic preview digest for reviewed dry-run binding."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.kernel.canonical_json import canonical_sha256
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.plan import (
    PlanEffectV1,
    PlanV1,
    SemanticDiffEntryV1,
)

PREVIEW_DIGEST_VERSION = "pd1"


def _diff_projection(entry: SemanticDiffEntryV1) -> dict[str, object]:
    return {
        "field_path": entry.field_path,
        "resource_id": entry.resource_id,
        "intent": entry.intent,
        "current": entry.current,
        "desired": entry.desired,
        "old": entry.old,
        "requested": entry.requested,
        "normalized": entry.normalized,
    }


def _effect_projection(effect: PlanEffectV1) -> dict[str, object]:
    return {
        "resource_id": effect.resource_id,
        "operation": effect.operation,
        "operation_index": effect.operation_index,
        "is_no_op": effect.is_no_op,
        "semantic_changes": [
            _diff_projection(change) for change in effect.semantic_changes
        ],
    }


def build_preview_projection(
    *,
    status: DryRunStatus,
    semantic_digest: str,
    state_tokens: dict[str, str],
    capability_projection_digest: str,
    plan: PlanV1 | None,
    diffs: list[SemanticDiffEntryV1],
) -> dict[str, object]:
    """Normative pd1 payload (design.md)."""
    effects: list[dict[str, object]] = []
    if plan is not None:
        effects = [_effect_projection(effect) for effect in plan.effects]
    actionable = [_diff_projection(entry) for entry in diffs]
    return {
        "version": PREVIEW_DIGEST_VERSION,
        "status": status.value,
        "semantic_digest": semantic_digest,
        "state_tokens": {k: state_tokens[k] for k in sorted(state_tokens)},
        "capability_projection_digest": capability_projection_digest,
        "plan_effects": effects,
        "diffs": actionable,
    }


def compute_preview_digest(
    *,
    status: DryRunStatus,
    semantic_digest: str,
    state_tokens: dict[str, str],
    capability_projection_digest: str,
    plan: PlanV1 | None,
    diffs: list[SemanticDiffEntryV1],
) -> str:
    """pd1_: binds reviewed preview; uses kernel canonical_json."""
    projection = build_preview_projection(
        status=status,
        semantic_digest=semantic_digest,
        state_tokens=state_tokens,
        capability_projection_digest=capability_projection_digest,
        plan=plan,
        diffs=diffs,
    )
    return canonical_sha256(projection, prefix="pd1_")
