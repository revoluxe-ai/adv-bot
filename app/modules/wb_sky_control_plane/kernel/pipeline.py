"""Read-only dry-run pipeline entrypoint."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_sky_control_plane.kernel.capabilities_eval import evaluate_capabilities
from app.modules.wb_sky_control_plane.kernel.preflight import collect_pure_preflight_errors
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
    """A1 dry-run: фаза A (pure) → resolve → фаза C (semantic validate/diff).

    Фаза A отклоняет без вызова resolver (PG SELECT / WB GET).
    ``validate_changeset`` не выполняет I/O. ``prior`` не сохраняется.
    """
    semantic_digest, pure_errors = collect_pure_preflight_errors(
        changeset,
        prior=prior,
        capability_grants=capability_grants,
    )
    if pure_errors:
        return DryRunResultV1(
            status=DryRunStatus.REJECTED,
            changeset_id=changeset.changeset_id,
            semantic_digest=semantic_digest,
            errors=pure_errors,
        )

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
        skip_pure_checks=True,
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
