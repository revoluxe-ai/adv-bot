"""Add auto_update_white_list to AdvSetting

Revision ID: 563a95f2f3bb
Revises: 42cfd1a692b5
Create Date: 2025-05-10 17:10:19.925383

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "563a95f2f3bb"
down_revision: str | None = "42cfd1a692b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "auto_update_white_list",
            sa.Boolean(),
            server_default="false",
            nullable=True,
        ),
    )


def downgrade() -> None:
    pass
