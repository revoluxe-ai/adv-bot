"""Apply Authority domain types and pure logic (Slice A).

Transport-independent Apply contract: request/context split, preview digests,
idempotency decisions, and receipt lifecycle rules. No persistence or writers.
"""

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.digest.capability_projection_digest import (
    CAPABILITY_PROJECTION_DIGEST_VERSION,
    compute_capability_projection_digest,
)
from app.modules.wb_sky_control_plane.apply.digest.preview_digest import (
    PREVIEW_DIGEST_VERSION,
    compute_preview_digest,
)
from app.modules.wb_sky_control_plane.apply.idempotency import (
    build_idempotency_fingerprint,
    decide_idempotency,
)
from app.modules.wb_sky_control_plane.apply.receipt_lifecycle import (
    apply_receipt_lifecycle_event,
    receipt_outcome_transition,
)

__all__ = [
    "APPLY_CONTRACT_VERSION",
    "CAPABILITY_PROJECTION_DIGEST_VERSION",
    "PREVIEW_DIGEST_VERSION",
    "apply_receipt_lifecycle_event",
    "build_idempotency_fingerprint",
    "compute_capability_projection_digest",
    "compute_preview_digest",
    "decide_idempotency",
    "receipt_outcome_transition",
]
