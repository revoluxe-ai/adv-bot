"""Add relevant_phrases (templates) to AdvSetting

Revision ID: f3a8e2c1d0ab
Revises: 90f2f60cb3ce
Create Date: 2026-03-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f3a8e2c1d0ab"
down_revision: Union[str, None] = "90f2f60cb3ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "relevant_phrases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
            comment=(
                "Шаблоны релевантных фраз (quoted exact + RE2 regex), как black_phrases"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("advsetting", "relevant_phrases")
