"""Add RaisePlanOnPromobonuses flag and promo allocation/spend journals.

Revision ID: c4f8a1b2d3e4
Revises: 0b0fe484ba6b
Create Date: 2026-09-06

Локальная schema-only миграция: флаг Plan, typed promo-поля журнала
пополнений и таблица списаний UPD. Не выполняет production data writes.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4f8a1b2d3e4"
down_revision: Union[str, None] = "0b0fe484ba6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advsetting",
        sa.Column(
            "raise_plan_on_promobonuses",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment=(
                "RaisePlanOnPromobonuses: разрешать увеличение Plan, "
                "если доступны промобонусы"
            ),
        ),
    )
    op.add_column(
        "wbautobudgettopup",
        sa.Column(
            "promo_amount",
            sa.Integer(),
            nullable=True,
            comment="Сумма промобонусов в пополнении; credit только при status=success",
        ),
    )
    op.add_column(
        "wbautobudgettopup",
        sa.Column(
            "promo_percent",
            sa.Integer(),
            nullable=True,
            comment="percent выбранного WB cashback-пакета",
        ),
    )
    op.add_column(
        "wbautobudgettopup",
        sa.Column(
            "promo_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="expiration_date исходного пакета common pool",
        ),
    )
    op.add_column(
        "wbautobudgettopup",
        sa.Column(
            "ordinary_amount",
            sa.Integer(),
            nullable=True,
            comment="Обычная доля пополнения (amount - promo_amount)",
        ),
    )
    op.create_table(
        "wbcampaignpromospend",
        sa.Column("advert_id", sa.BIGINT(), nullable=False, comment="WB advertId кампании"),
        sa.Column("upd_num", sa.Integer(), nullable=True, comment="Номер УПД, если WB его вернул"),
        sa.Column(
            "upd_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Время списания из UPD",
        ),
        sa.Column("upd_sum", sa.Integer(), nullable=False, comment="Сумма списания промо, ₽"),
        sa.Column(
            "payment_type",
            sa.String(length=64),
            nullable=False,
            comment="Исходный paymentType WB (Кэшбэк/Keshbek)",
        ),
        sa.Column(
            "fingerprint",
            sa.String(length=128),
            nullable=False,
            comment="Идемпотентный ключ строки UPD",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_wbcampaignpromospend_fingerprint"),
    )
    op.create_index(
        "ix_wbcampaignpromospend_advert_id",
        "wbcampaignpromospend",
        ["advert_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wbcampaignpromospend_advert_id", table_name="wbcampaignpromospend")
    op.drop_table("wbcampaignpromospend")
    op.drop_column("wbautobudgettopup", "ordinary_amount")
    op.drop_column("wbautobudgettopup", "promo_expires_at")
    op.drop_column("wbautobudgettopup", "promo_percent")
    op.drop_column("wbautobudgettopup", "promo_amount")
    op.drop_column("advsetting", "raise_plan_on_promobonuses")
