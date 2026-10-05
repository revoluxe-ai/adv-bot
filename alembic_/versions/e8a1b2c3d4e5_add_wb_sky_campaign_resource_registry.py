"""Add wb sky campaign resource registry table

Stable opaque cmp_* resource identity for existing logical campaign resources.
Canonical identity не добавляется в AdvSetting.

Revision ID: e8a1b2c3d4e5
Revises: d7e3c9f1a204
Create Date: 2026-10-03 10:15:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e8a1b2c3d4e5"
down_revision: str | None = "d7e3c9f1a204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wbskycampaignresourceregistry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("wb_cabinet_id", sa.Integer(), nullable=False),
        sa.Column("adv_setting_id", sa.Integer(), nullable=True),
        sa.Column("auto_adv_id", sa.Integer(), nullable=True),
        sa.Column("search_adv_id", sa.Integer(), nullable=True),
        sa.Column("anchor_fingerprint", sa.String(length=128), nullable=False),
        sa.Column(
            "backfill_status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adv_setting_id"),
        sa.UniqueConstraint("resource_id"),
        sa.UniqueConstraint(
            "wb_cabinet_id",
            "anchor_fingerprint",
            name="uq_wbsky_registry_cabinet_anchor",
        ),
    )
    op.create_index(
        "ix_wbsky_registry_auto_adv_id",
        "wbskycampaignresourceregistry",
        ["auto_adv_id"],
        unique=False,
    )
    op.create_index(
        "ix_wbsky_registry_search_adv_id",
        "wbskycampaignresourceregistry",
        ["search_adv_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_wbskycampaignresourceregistry_wb_cabinet_id"),
        "wbskycampaignresourceregistry",
        ["wb_cabinet_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_wbskycampaignresourceregistry_wb_cabinet_id"),
        table_name="wbskycampaignresourceregistry",
    )
    op.drop_index(
        "ix_wbsky_registry_search_adv_id",
        table_name="wbskycampaignresourceregistry",
    )
    op.drop_index(
        "ix_wbsky_registry_auto_adv_id",
        table_name="wbskycampaignresourceregistry",
    )
    op.drop_table("wbskycampaignresourceregistry")
