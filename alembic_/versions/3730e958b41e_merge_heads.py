"""merge heads

Revision ID: 3730e958b41e
Revises: 0cf5b8a2edf8, 2e38438b0f7e
Create Date: 2025-09-18 08:23:55.678119

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3730e958b41e"
down_revision: str | None = ("0cf5b8a2edf8", "2e38438b0f7e")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
