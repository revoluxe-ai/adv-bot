"""Idempotency fingerprint and pure decisions."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
    IdempotencyDecisionKind,
)
from app.modules.wb_sky_control_plane.apply.idempotency import (
    IdempotencyRecordView,
    build_idempotency_fingerprint,
    decide_idempotency,
)
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.models.changeset import LogicalScopeV1

pytestmark = pytest.mark.unit


def _evidence() -> ApplyEvidenceV1:
    return ApplyEvidenceV1(
        evidence_id="ev_1",
        scope=LogicalScopeV1(shop_id="shop1"),
        changeset_id="cs_1",
        dry_run_receipt_id="rcpt_1",
        idempotency_key="key1",
        apply_contract_version=APPLY_CONTRACT_VERSION,
        semantic_digest="sd1_a",
        preview_digest="pd1_a",
        terminal_status=ApplyTerminalStatus.VERIFIED,
        committed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_fingerprint_changes_when_pd1_changes() -> None:
    f1 = build_idempotency_fingerprint(
        apply_contract_version=APPLY_CONTRACT_VERSION,
        semantic_digest="sd1_x",
        preview_digest="pd1_x",
    )
    f2 = build_idempotency_fingerprint(
        apply_contract_version=APPLY_CONTRACT_VERSION,
        semantic_digest="sd1_x",
        preview_digest="pd1_y",
    )
    assert f1 != f2


def test_unauthorized_replay_hides_evidence() -> None:
    fp = build_idempotency_fingerprint(
        apply_contract_version=APPLY_CONTRACT_VERSION,
        semantic_digest="sd1_a",
        preview_digest="pd1_a",
    )
    record = IdempotencyRecordView(
        fingerprint=fp,
        terminal_status=ApplyTerminalStatus.VERIFIED,
        in_flight=False,
        evidence=_evidence(),
    )
    decision = decide_idempotency(
        fingerprint=fp, record=record, caller_authorized=False
    )
    assert decision.kind == IdempotencyDecisionKind.REPLAY_CANDIDATE
    assert decision.reason_code == ApplyReasonCode.UNAUTHORIZED
    assert decision.evidence is None


def test_idempotency_conflict() -> None:
    fp_a = build_idempotency_fingerprint(
        apply_contract_version=APPLY_CONTRACT_VERSION,
        semantic_digest="sd1_a",
        preview_digest="pd1_a",
    )
    fp_b = build_idempotency_fingerprint(
        apply_contract_version=APPLY_CONTRACT_VERSION,
        semantic_digest="sd1_b",
        preview_digest="pd1_a",
    )
    record = IdempotencyRecordView(
        fingerprint=fp_a,
        terminal_status=ApplyTerminalStatus.VERIFIED,
        in_flight=False,
        evidence=_evidence(),
    )
    decision = decide_idempotency(
        fingerprint=fp_b, record=record, caller_authorized=True
    )
    assert decision.kind == IdempotencyDecisionKind.CONFLICT
    assert decision.reason_code == ApplyReasonCode.IDEMPOTENCY_CONFLICT
