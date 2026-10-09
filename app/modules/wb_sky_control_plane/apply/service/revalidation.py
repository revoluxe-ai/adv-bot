"""Authoritative dry-run projection for apply binding (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_sky_control_plane.apply.digest.capability_projection_digest import (
    compute_capability_projection_digest,
)
from app.modules.wb_sky_control_plane.apply.digest.preview_digest import (
    compute_preview_digest,
)
from app.modules.wb_sky_control_plane.kernel.capabilities_eval import evaluate_capabilities
from app.modules.wb_sky_control_plane.kernel.preflight import collect_pure_preflight_errors
from app.modules.wb_sky_control_plane.kernel.validate import validate_changeset
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError
from app.modules.wb_sky_control_plane.models.plan import PlanV1, SemanticDiffEntryV1
from app.modules.wb_sky_control_plane.models.snapshot import CampaignResourceSnapshotV1
from app.modules.wb_sky_control_plane.ports.wb_read_port import WbPromotionV2ReadPort
from app.modules.wb_sky_control_plane.read.resolver import resolve_changeset_snapshots


@dataclass(frozen=True, slots=True)
class ApplyBindingMaterial:
    """Server-recomputed binding fields for receipt compare and idempotency."""

    status: DryRunStatus
    semantic_digest: str
    preview_digest: str
    capability_projection_digest: str
    state_tokens: dict[str, str]
    plan: PlanV1 | None
    diffs: list[SemanticDiffEntryV1]
    snapshots: dict[str, CampaignResourceSnapshotV1]
    errors: list[ControlPlaneError]


async def project_apply_binding_material(
    changeset: ChangeSetV1,
    *,
    session: AsyncSession,
    wb_reader: WbPromotionV2ReadPort,
) -> ApplyBindingMaterial:
    """Resolve + validate ChangeSet without writes (same phases as ``dry_run``)."""
    semantic_digest, pure_errors = collect_pure_preflight_errors(changeset)
    if pure_errors:
        return ApplyBindingMaterial(
            status=DryRunStatus.REJECTED,
            semantic_digest=semantic_digest,
            preview_digest="",
            capability_projection_digest="",
            state_tokens={},
            plan=None,
            diffs=[],
            snapshots={},
            errors=pure_errors,
        )

    snapshots, resolve_errors = await resolve_changeset_snapshots(
        changeset, session=session, wb_reader=wb_reader
    )
    if resolve_errors:
        return ApplyBindingMaterial(
            status=DryRunStatus.REJECTED,
            semantic_digest=semantic_digest,
            preview_digest="",
            capability_projection_digest="",
            state_tokens={},
            plan=None,
            diffs=[],
            snapshots={},
            errors=resolve_errors,
        )

    capabilities = {
        resource_id: evaluate_capabilities(snapshot)
        for resource_id, snapshot in snapshots.items()
    }
    validated = validate_changeset(
        changeset,
        snapshots,
        capabilities,
        skip_pure_checks=True,
    )
    state_tokens = {
        rid: snap.state_token or ""
        for rid, snap in snapshots.items()
        if snap.state_token
    }
    cpd1 = compute_capability_projection_digest(capabilities)
    pd1 = compute_preview_digest(
        status=validated.status,
        semantic_digest=validated.semantic_digest,
        state_tokens=state_tokens,
        capability_projection_digest=cpd1,
        plan=validated.plan,
        diffs=validated.diffs,
    )
    return ApplyBindingMaterial(
        status=validated.status,
        semantic_digest=validated.semantic_digest,
        preview_digest=pd1,
        capability_projection_digest=cpd1,
        state_tokens=state_tokens,
        plan=validated.plan,
        diffs=validated.diffs,
        snapshots=snapshots,
        errors=validated.errors,
    )
