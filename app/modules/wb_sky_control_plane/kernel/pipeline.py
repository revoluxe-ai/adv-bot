"""Read-only dry-run pipeline entrypoint."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_sky_control_plane.kernel.capabilities_eval import evaluate_capabilities
from app.modules.wb_sky_control_plane.kernel.semantic_digest import compute_semantic_digest
from app.modules.wb_sky_control_plane.kernel.validate import validate_changeset
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.plan import (
    DryRunResultV1,
    PriorChangeSetRecord,
)
from app.modules.wb_sky_control_plane.ports.wb_read_port import WbPromotionV2ReadPort
from app.modules.wb_sky_control_plane.read.resolver import resolve_changeset_snapshots


async def dry_run(
    changeset: ChangeSetV1,
    *,
    session: AsyncSession,
    wb_reader: WbPromotionV2ReadPort,
    prior: PriorChangeSetRecord | None = None,
    capability_grants: frozenset[str] | None = None,
) -> DryRunResultV1:
    """Execute A1 read-only pipeline: resolve → classify → validate → diff.

    Side effects: read-only SQL SELECT and read-only WB HTTP GET only.
    ``validate_changeset`` itself performs no I/O. ``prior`` is not persisted.
    No ORM DML/flush/commit and no WB mutation calls.
    """
    semantic_digest = compute_semantic_digest(changeset)
    snapshots, resolve_errors = await resolve_changeset_snapshots(
        changeset, session=session, wb_reader=wb_reader
    )
    if resolve_errors:
        return DryRunResultV1(
            status=DryRunStatus.REJECTED,
            changeset_id=changeset.changeset_id,
            semantic_digest=semantic_digest,
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
        prior=prior,
        capability_grants=capability_grants,
    )
    return DryRunResultV1(
        status=validated.status,
        changeset_id=changeset.changeset_id,
        semantic_digest=validated.semantic_digest,
        plan=validated.plan,
        errors=validated.errors,
        state_tokens={
            rid: snap.state_token or ""
            for rid, snap in snapshots.items()
            if snap.state_token
        },
    )
