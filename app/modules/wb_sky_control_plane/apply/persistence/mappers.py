"""Map ORM rows ↔ Apply domain models."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyAttemptLifecycleState,
    ApplyReasonCode,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
    TransportChannel,
)
from app.modules.wb_sky_control_plane.apply.models.attempt import ApplyAttemptRecordV1
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.apply.models.receipt import (
    DryRunReceiptBindingV1,
    DryRunReceiptV1,
)
from app.modules.wb_sky_control_plane.apply.persistence.models import (
    WbSkyApplyAttemptRecord,
    WbSkyApplyDryRunReceipt,
    WbSkyApplyEvidence,
)
from typing import Literal, cast

from app.modules.wb_sky_control_plane.models.changeset import LogicalScopeV1
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus


def receipt_row_to_domain(row: WbSkyApplyDryRunReceipt) -> DryRunReceiptV1:
    binding = DryRunReceiptBindingV1(
        receipt_id=row.receipt_id,
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        scope=LogicalScopeV1(
            provider=cast(Literal["wildberries"], row.scope_provider),
            shop_id=row.shop_id,
        ),
        changeset_id=row.changeset_id,
        semantic_digest=row.semantic_digest,
        preview_digest=row.preview_digest,
        state_tokens=dict(row.state_tokens),
        capability_projection_digest=row.capability_projection_digest,
        dry_run_status=DryRunStatus(row.dry_run_status),
    )
    return DryRunReceiptV1(
        binding=binding,
        lifecycle_state=DryRunReceiptLifecycleState(row.lifecycle_state),
    )


def evidence_row_to_domain(row: WbSkyApplyEvidence) -> ApplyEvidenceV1:
    return ApplyEvidenceV1(
        evidence_id=row.evidence_id,
        scope=LogicalScopeV1(
            provider=cast(Literal["wildberries"], row.scope_provider),
            shop_id=row.shop_id,
        ),
        changeset_id=row.changeset_id,
        dry_run_receipt_id=row.dry_run_receipt_id,
        idempotency_key=row.idempotency_key,
        apply_contract_version=row.apply_contract_version,
        semantic_digest=row.semantic_digest,
        preview_digest=row.preview_digest,
        post_state_tokens=dict(row.post_state_tokens),
        terminal_status=ApplyTerminalStatus(row.terminal_status),
        committed_at=row.committed_at,
    )


def attempt_row_to_domain(row: WbSkyApplyAttemptRecord) -> ApplyAttemptRecordV1:
    return ApplyAttemptRecordV1(
        attempt_id=row.attempt_id,
        shop_id=row.shop_id,
        idempotency_key=row.idempotency_key,
        dry_run_receipt_id=row.dry_run_receipt_id,
        principal_kind=row.principal_kind,
        principal_id=row.principal_id,
        transport_channel=TransportChannel(row.transport_channel),
        lifecycle_state=ApplyAttemptLifecycleState(row.lifecycle_state),
        terminal_status=(
            ApplyTerminalStatus(row.terminal_status) if row.terminal_status else None
        ),
        reason_code=(
            ApplyReasonCode(row.reason_code) if row.reason_code else None
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
