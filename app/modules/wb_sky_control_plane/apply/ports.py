"""Apply Authority ports (Slice A protocols; Slice B+ implementations)."""

from __future__ import annotations

from typing import Protocol

from app.modules.wb_sky_control_plane.apply.idempotency import IdempotencyKey
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.apply.models.receipt import DryRunReceiptV1


class DryRunReceiptStorePort(Protocol):
    """Persisted dry-run receipts (Slice B)."""

    async def get_by_id(self, receipt_id: str) -> DryRunReceiptV1 | None:
        """Load receipt by id."""
        ...


class IdempotencyStorePort(Protocol):
    """Idempotency ledger (Slice B)."""

    async def get(
        self, key: IdempotencyKey
    ) -> tuple[str, ApplyEvidenceV1 | None, bool] | None:
        """Return fingerprint, evidence, in_flight — or None if missing."""
        ...
