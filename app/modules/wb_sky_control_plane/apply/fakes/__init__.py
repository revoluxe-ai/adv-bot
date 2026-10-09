"""In-memory fakes for unit tests (Slice A only)."""

from app.modules.wb_sky_control_plane.apply.fakes.memory import (
    InMemoryDryRunReceiptStore,
    InMemoryIdempotencyStore,
)

__all__ = ["InMemoryDryRunReceiptStore", "InMemoryIdempotencyStore"]
