"""
Formal idempotency adapter contract for ad-control Apply (Slice B).

Runtime durable idempotency is **not** implemented until Apply Authority wires
ad-control mutations. This module defines binding to the existing ledger only.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.wb_sky_control_plane.apply.idempotency import (
    IdempotencyDecision,
    IdempotencyRecordView,
    build_idempotency_fingerprint,
    decide_idempotency,
)
from app.modules.wb_sky_control_plane.kernel.ad_control_validate import (
    compute_ad_control_semantic_digest,
)
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetV1,
)


@dataclass(frozen=True, slots=True)
class AdControlIdempotencyBinding:
    """
    Semantic digest + fingerprint vocabulary for future Apply adapter.

    Same ``(shop_id, idempotency_key)`` + same fingerprint => replay-safe.
    Same key + different fingerprint => ``FINGERPRINT_MISMATCH`` conflict.
    """

    semantic_digest: str
    fingerprint: str


def bind_ad_control_idempotency(
    changeset: AdControlChangeSetV1,
    *,
    apply_contract_version: str,
    preview_digest: str,
) -> AdControlIdempotencyBinding:
    """Compute sd1 + idf1 binding without storage I/O."""
    semantic_digest = compute_ad_control_semantic_digest(changeset)
    fingerprint = build_idempotency_fingerprint(
        apply_contract_version=apply_contract_version,
        semantic_digest=semantic_digest,
        preview_digest=preview_digest,
    )
    return AdControlIdempotencyBinding(
        semantic_digest=semantic_digest,
        fingerprint=fingerprint,
    )


def evaluate_ad_control_idempotency_replay(
    *,
    binding: AdControlIdempotencyBinding,
    record: IdempotencyRecordView | None,
    caller_authorized: bool,
) -> IdempotencyDecision:
    """Pure replay decision — reuses Apply Authority ``decide_idempotency``."""
    return decide_idempotency(
        fingerprint=binding.fingerprint,
        record=record,
        caller_authorized=caller_authorized,
    )
