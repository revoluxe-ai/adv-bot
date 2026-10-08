"""Test-only in-memory port fakes (no production use)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.wb_sky_control_plane.apply.idempotency import (
    IdempotencyKey,
    IdempotencyRecordView,
)
from app.modules.wb_sky_control_plane.apply.models.receipt import DryRunReceiptV1


def _new_receipt_map() -> dict[str, DryRunReceiptV1]:
    return {}


def _new_idempotency_map() -> dict[tuple[str, str], IdempotencyRecordView]:
    return {}


@dataclass
class InMemoryDryRunReceiptStore:
    """Mutable in-memory receipt bag for tests."""

    _rows: dict[str, DryRunReceiptV1] = field(default_factory=_new_receipt_map)

    async def get_by_id(self, receipt_id: str) -> DryRunReceiptV1 | None:
        return self._rows.get(receipt_id)

    def put(self, receipt: DryRunReceiptV1) -> None:
        self._rows[receipt.binding.receipt_id] = receipt


@dataclass
class InMemoryIdempotencyStore:
    """In-memory idempotency view backing decide_idempotency tests."""

    _rows: dict[tuple[str, str], IdempotencyRecordView] = field(
        default_factory=_new_idempotency_map
    )

    def put(self, key: IdempotencyKey, record: IdempotencyRecordView) -> None:
        self._rows[(key.shop_id, key.idempotency_key)] = record

    def get_view(self, key: IdempotencyKey) -> IdempotencyRecordView | None:
        return self._rows.get((key.shop_id, key.idempotency_key))
