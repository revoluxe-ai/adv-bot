"""Порт append-only persistence attribution observations (Slice C)."""

from __future__ import annotations

from typing import Protocol

from app.modules.attribution_facts.domain.ingest_models import AttributionIngestBatch


class AttributionObservationWriter(Protocol):
    """Append ingest batch to durable store; idempotent by observation_id."""

    async def append_batch(self, batch: AttributionIngestBatch) -> None:
        """
        Persist facts + reconciliation metadata.

        Duplicate observation_id rows MUST NOT change latest logical projection.
        """
        ...
