"""Add FK admin_user_id -> user.id to WBBonusPayment

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-07

Fixes semantic mismatch: admin_user_id must reference User.id (internal PK),
not telegram_id. Migrates existing rows that stored telegram_id.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix existing data: admin_user_id may hold telegram_id. Resolve to User.id.
    op.execute("""
        UPDATE wbbonuspayment wbp
        SET admin_user_id = u.id
        FROM "user" u
        WHERE u.user_telegram_id = wbp.admin_user_id
        AND wbp.admin_user_id IS NOT NULL
    """)
    # Set NULL where value is not a valid User.id (orphaned telegram_ids)
    op.execute("""
        UPDATE wbbonuspayment
        SET admin_user_id = NULL
        WHERE admin_user_id IS NOT NULL
        AND admin_user_id NOT IN (SELECT id FROM "user")
    """)
    op.create_foreign_key(
        "fk_wbbonuspayment_admin_user_id_user",
        "wbbonuspayment",
        "user",
        ["admin_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_wbbonuspayment_admin_user_id_user",
        "wbbonuspayment",
        type_="foreignkey",
    )
