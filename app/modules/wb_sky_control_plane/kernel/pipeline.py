"""Read-only dry-run pipeline entrypoint."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_sky_control_plane.kernel.capabilities_eval import evaluate_capabilities
from app.modules.wb_sky_control_plane.kernel.planner import build_plan
from app.modules.wb_sky_control_plane.kernel.semantic_digest import compute_semantic_digest
from app.modules.wb_sky_control_plane.kernel.validate import validate_changeset
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.plan import DryRunResultV1
from app.modules.wb_sky_control_plane.ports.wb_read_port import WbPromotionV2ReadPort
from app.modules.wb_sky_control_plane.read.resolver import resolve_changeset_snapshots


async def dry_run(
    changeset: ChangeSetV1,
    *,
    session: AsyncSession,
    wb_reader: WbPromotionV2ReadPort,
) -> DryRunResultV1:
    """Execute A1 read-only pipeline: resolve → classify → validate → plan.

    Side effects: read-only SQL SELECT and read-only WB HTTP GET only.
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
    validation_errors = validate_changeset(changeset, snapshots, capabilities)
    if validation_errors:
        return DryRunResultV1(
            status=DryRunStatus.REJECTED,
            changeset_id=changeset.changeset_id,
            semantic_digest=semantic_digest,
            errors=validation_errors,
            state_tokens={
                rid: snap.state_token or ""
                for rid, snap in snapshots.items()
                if snap.state_token
            },
        )

    plan = build_plan(changeset.operations, snapshots)
    status = DryRunStatus.NO_OP if plan.is_no_op else DryRunStatus.OK
    return DryRunResultV1(
        status=status,
        changeset_id=changeset.changeset_id,
        semantic_digest=semantic_digest,
        plan=plan,
        state_tokens={
            rid: snap.state_token or ""
            for rid, snap in snapshots.items()
            if snap.state_token
        },
    )
