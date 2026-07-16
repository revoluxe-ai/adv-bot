"""Add partner payout table

Revision ID: 6d3ef9bb7a12
Revises: 4f6c1dcf2b7a
Create Date: 2026-06-24 18:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6d3ef9bb7a12"
down_revision: Union[str, None] = "4f6c1dcf2b7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "partner_payout",
        sa.Column("partner_user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_admin_user_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["partner_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_partner_payout_partner_user_id",
        "partner_payout",
        ["partner_user_id"],
        unique=False,
    )
    op.create_index(
        "idx_partner_payout_created_by_admin_user_id",
        "partner_payout",
        ["created_by_admin_user_id"],
        unique=False,
    )
    op.create_index(
        "idx_partner_payout_created_at",
        "partner_payout",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_partner_payout_created_at", table_name="partner_payout")
    op.drop_index(
        "idx_partner_payout_created_by_admin_user_id",
        table_name="partner_payout",
    )
    op.drop_index(
        "idx_partner_payout_partner_user_id",
        table_name="partner_payout",
    )
    op.drop_table("partner_payout")
