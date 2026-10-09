"""Add ad control settings persistence tables

Shop + campaign configured feature rows (JSONB representation).

Revision ID: b1c2d3e4f5a7
Revises: f9c0a1b2d3e4
Create Date: 2026-10-09 14:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5a7"
down_revision: str | None = "f9c0a1b2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "adcontrolshopfeaturerow",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shop_id", sa.String(length=128), nullable=False),
        sa.Column("feature_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("activation", sa.String(length=16), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("state_token", sa.String(length=128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "feature_id",
            name="uq_ad_control_shop_feature_identity",
        ),
    )
    op.create_index(
        "ix_ad_control_shop_feature_lookup",
        "adcontrolshopfeaturerow",
        ["shop_id", "feature_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adcontrolshopfeaturerow_shop_id"),
        "adcontrolshopfeaturerow",
        ["shop_id"],
        unique=False,
    )

    op.create_table(
        "adcontrolcampaignfeaturerow",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shop_id", sa.String(length=128), nullable=False),
        sa.Column("advert_id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("state_token", sa.String(length=128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "advert_id",
            "feature_id",
            name="uq_ad_control_campaign_feature_identity",
        ),
    )
    op.create_index(
        "ix_ad_control_campaign_feature_lookup",
        "adcontrolcampaignfeaturerow",
        ["shop_id", "advert_id", "feature_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adcontrolcampaignfeaturerow_shop_id"),
        "adcontrolcampaignfeaturerow",
        ["shop_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_adcontrolcampaignfeaturerow_shop_id"),
        table_name="adcontrolcampaignfeaturerow",
    )
    op.drop_index(
        "ix_ad_control_campaign_feature_lookup",
        table_name="adcontrolcampaignfeaturerow",
    )
    op.drop_table("adcontrolcampaignfeaturerow")
    op.drop_index(
        op.f("ix_adcontrolshopfeaturerow_shop_id"),
        table_name="adcontrolshopfeaturerow",
    )
    op.drop_index(
        "ix_ad_control_shop_feature_lookup",
        table_name="adcontrolshopfeaturerow",
    )
    op.drop_table("adcontrolshopfeaturerow")
