"""Add user invite/gate fields (passed_gate, passed_gate_at, passed_gate_reason, last_invite_issued_at)

Revision ID: a1b2c3d4e5f6
Revises: 8d63800302cc
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8d63800302cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

passed_gate_reason_enum = sa.Enum(
    "BALANCE_TOP_UP",
    "INVITE_CODE_ENTRY",
    name="passedgatereason",
)


def upgrade() -> None:
    passed_gate_reason_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "user",
        sa.Column(
            "passed_gate",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "user",
        sa.Column("passed_gate_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "passed_gate_reason",
            sa.Enum("BALANCE_TOP_UP", "INVITE_CODE_ENTRY", name="passedgatereason"),
            nullable=True,
        ),
    )
    op.add_column(
        "user",
        sa.Column("last_invite_issued_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "last_invite_issued_at")
    op.drop_column("user", "passed_gate_reason")
    op.drop_column("user", "passed_gate_at")
    op.drop_column("user", "passed_gate")
    passed_gate_reason_enum.drop(op.get_bind(), checkfirst=True)
