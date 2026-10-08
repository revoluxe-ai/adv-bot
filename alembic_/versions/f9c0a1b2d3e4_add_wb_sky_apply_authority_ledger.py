"""Add WB Sky Apply Authority PG ledger tables (Slice B).

Dry-run receipt, idempotency, attempt lifecycle, immutable evidence.

Revision ID: f9c0a1b2d3e4
Revises: e8a1b2c3d4e5
Create Date: 2026-10-08 23:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f9c0a1b2d3e4"
down_revision: str | None = "e8a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wbskyapplydryrunreceipt",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("receipt_id", sa.String(length=128), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope_provider", sa.String(length=32), nullable=False),
        sa.Column("shop_id", sa.String(length=128), nullable=False),
        sa.Column("changeset_id", sa.String(length=128), nullable=False),
        sa.Column("semantic_digest", sa.String(length=128), nullable=False),
        sa.Column("preview_digest", sa.String(length=128), nullable=False),
        sa.Column(
            "state_tokens",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("capability_projection_digest", sa.String(length=128), nullable=False),
        sa.Column("dry_run_status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_id"),
    )
    op.create_index(
        "ix_wbsky_apply_receipt_shop_lifecycle",
        "wbskyapplydryrunreceipt",
        ["shop_id", "lifecycle_state"],
        unique=False,
    )

    op.create_table(
        "wbskyapplyidempotencyledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shop_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("in_flight", sa.Boolean(), nullable=False),
        sa.Column("terminal_status", sa.String(length=32), nullable=True),
        sa.Column("evidence_id", sa.String(length=128), nullable=True),
        sa.Column("attempt_id", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "idempotency_key",
            name="uq_wbsky_apply_idempotency_shop_key",
        ),
    )

    op.create_table(
        "wbskyapplyattemptrecord",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.String(length=128), nullable=False),
        sa.Column("shop_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("dry_run_receipt_id", sa.String(length=128), nullable=False),
        sa.Column("principal_kind", sa.String(length=32), nullable=False),
        sa.Column("principal_id", sa.String(length=256), nullable=False),
        sa.Column("transport_channel", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("terminal_status", sa.String(length=32), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id"),
    )
    op.create_index(
        "ix_wbskyapplyattemptrecord_shop_id",
        "wbskyapplyattemptrecord",
        ["shop_id"],
        unique=False,
    )

    op.create_table(
        "wbskyapplyevidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evidence_id", sa.String(length=128), nullable=False),
        sa.Column("scope_provider", sa.String(length=32), nullable=False),
        sa.Column("shop_id", sa.String(length=128), nullable=False),
        sa.Column("changeset_id", sa.String(length=128), nullable=False),
        sa.Column("dry_run_receipt_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("apply_contract_version", sa.String(length=32), nullable=False),
        sa.Column("semantic_digest", sa.String(length=128), nullable=False),
        sa.Column("preview_digest", sa.String(length=128), nullable=False),
        sa.Column(
            "post_state_tokens",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("terminal_status", sa.String(length=32), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id"),
    )
    op.create_index(
        "ix_wbskyapplyevidence_shop_id",
        "wbskyapplyevidence",
        ["shop_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wbskyapplyevidence_shop_id", table_name="wbskyapplyevidence")
    op.drop_table("wbskyapplyevidence")
    op.drop_index("ix_wbskyapplyattemptrecord_shop_id", table_name="wbskyapplyattemptrecord")
    op.drop_table("wbskyapplyattemptrecord")
    op.drop_table("wbskyapplyidempotencyledger")
    op.drop_index(
        "ix_wbsky_apply_receipt_shop_lifecycle",
        table_name="wbskyapplydryrunreceipt",
    )
    op.drop_table("wbskyapplydryrunreceipt")
