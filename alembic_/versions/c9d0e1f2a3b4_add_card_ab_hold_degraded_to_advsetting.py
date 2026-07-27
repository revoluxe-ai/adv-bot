"""Add card_ab_hold_degraded to AdvSetting

Revision ID: c9d0e1f2a3b4
Revises: e1f2a3b4c5d6
Create Date: 2026-07-14

Spec card-ab-hold-mode §8 / decision write-path §8: durable PG-флаг честной
деградации A/B Hold. Enforcement замороженного allowed-set ограничен WB minus
cap; при превышении (или open-match без доказанной controllability) система
MUST деградировать видимо — лог И честный статус. Флаг — durable source of
truth для UI-рендера (bot-под читает его отдельно от shop-runner-пода, где
считается enforcement). Self-healing: снимается на тике, где cap не превышен.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "card_ab_hold_degraded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment=(
                "A/B Hold honest degradation: True когда enforcement замороженного "
                "allowed-set не может гарантировать чистый hold (WB minus cap / "
                "open-match) (spec card-ab-hold-mode §8)"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("advsetting", "card_ab_hold_degraded")
