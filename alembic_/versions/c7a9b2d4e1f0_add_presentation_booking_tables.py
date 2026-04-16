"""Add presentation booking tables

Revision ID: c7a9b2d4e1f0
Revises: f3a8e2c1d0ab
Create Date: 2026-04-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7a9b2d4e1f0"
down_revision: Union[str, None] = "f3a8e2c1d0ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    presentation_booking_status = sa.Enum(
        "booked", "cancelled", name="presentationbookingstatus"
    )
    presentation_booking_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "presentation_slot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column(
            "duration_minutes",
            sa.Integer(),
            server_default=sa.text("60"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_presentation_slot_start_at",
        "presentation_slot",
        ["start_at"],
        unique=False,
    )
    op.create_index(
        "ix_presentation_slot_is_active_start_at",
        "presentation_slot",
        ["is_active", "start_at"],
        unique=False,
    )

    op.create_table(
        "presentation_booking",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("booked", "cancelled", name="presentationbookingstatus"),
            server_default=sa.text("'booked'"),
            nullable=False,
        ),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["slot_id"], ["presentation_slot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slot_id", name="uq_presentation_booking_slot_id"),
    )
    op.create_index(
        "ix_presentation_booking_user_id_status",
        "presentation_booking",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_presentation_booking_user_id_status",
        table_name="presentation_booking",
    )
    op.drop_table("presentation_booking")
    op.drop_index(
        "ix_presentation_slot_is_active_start_at",
        table_name="presentation_slot",
    )
    op.drop_index("ix_presentation_slot_start_at", table_name="presentation_slot")
    op.drop_table("presentation_slot")

    presentation_booking_status = sa.Enum(
        "booked", "cancelled", name="presentationbookingstatus"
    )
    presentation_booking_status.drop(op.get_bind(), checkfirst=True)
