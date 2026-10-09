"""ORM models Apply Authority PG ledger (immutable binding columns + lifecycle)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class WbSkyApplyDryRunReceipt(BaseTable):
    """Server-issued dry-run receipt; binding immutable, lifecycle mutable."""

    receipt_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scope_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    shop_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    changeset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    semantic_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    preview_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    state_tokens: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    capability_projection_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    dry_run_status: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        Index("ix_wbsky_apply_receipt_shop_lifecycle", "shop_id", "lifecycle_state"),
    )


class WbSkyApplyIdempotencyLedger(BaseTable):
    """Idempotency slot per (shop_id, idempotency_key)."""

    shop_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    in_flight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    terminal_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "idempotency_key",
            name="uq_wbsky_apply_idempotency_shop_key",
        ),
    )


class WbSkyApplyAttemptRecord(BaseTable):
    """Mutable apply attempt lifecycle."""

    attempt_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    shop_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    dry_run_receipt_id: Mapped[str] = mapped_column(String(128), nullable=False)
    principal_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(256), nullable=False)
    transport_channel: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    terminal_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WbSkyApplyEvidence(BaseTable):
    """Insert-only execution evidence."""

    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    scope_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    shop_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    changeset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dry_run_receipt_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    apply_contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    semantic_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    preview_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    post_state_tokens: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    terminal_status: Mapped[str] = mapped_column(String(32), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
