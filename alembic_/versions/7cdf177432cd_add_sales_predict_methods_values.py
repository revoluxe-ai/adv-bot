"""Add new values to sales_predict_method enum.

Revision ID: 7cdf177432cd
Revises: b6c7df510683
Create Date: 2025-10-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7cdf177432cd"
down_revision: Union[str, None] = "b6c7df510683"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE factmethods ADD VALUE IF NOT EXISTS 'BY_WEIGHT_BY_CARTS'"
    )
    op.execute(
        "ALTER TYPE factmethods ADD VALUE IF NOT EXISTS 'BY_WEIGHT_BY_DIRECT_SALES'"
    )


def downgrade() -> None:
    # Downgrade is a no-op because removing enum values is unsafe.
    pass
