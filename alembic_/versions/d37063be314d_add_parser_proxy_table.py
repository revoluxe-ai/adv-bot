"""Add parser proxy table

Revision ID: d37063be314d
Revises: c155b8abb7c9
Create Date: 2024-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d37063be314d"
down_revision: Union[str, None] = "c155b8abb7c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parser_proxy",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scheme", sa.String(length=16), nullable=False, server_default=sa.text("'http'")),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cooldown_until", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("host", "port", name="uq_parser_proxy_host_port"),
    )
    op.create_index(
        "ix_parser_proxy_scheme", "parser_proxy", ["scheme"], unique=False
    )
    op.create_index(
        "ix_parser_proxy_is_active", "parser_proxy", ["is_active"], unique=False
    )
    op.create_index(
        "ix_parser_proxy_last_used_at", "parser_proxy", ["last_used_at"], unique=False
    )
    op.create_index(
        "ix_parser_proxy_fail_count", "parser_proxy", ["fail_count"], unique=False
    )
    op.create_index(
        "ix_parser_proxy_cooldown_until",
        "parser_proxy",
        ["cooldown_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_parser_proxy_cooldown_until", table_name="parser_proxy")
    op.drop_index("ix_parser_proxy_fail_count", table_name="parser_proxy")
    op.drop_index("ix_parser_proxy_last_used_at", table_name="parser_proxy")
    op.drop_index("ix_parser_proxy_is_active", table_name="parser_proxy")
    op.drop_index("ix_parser_proxy_scheme", table_name="parser_proxy")
    op.drop_table("parser_proxy")
