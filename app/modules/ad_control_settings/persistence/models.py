"""ORM rows configured hierarchical ad control (shop + campaign scopes)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class AdControlShopFeatureRow(BaseTable):
    """
    Shop-level feature slot: activation + optional typed payload.

    Logical identity: ``(shop_id, feature_id)``.
    ``schema_version`` is a column on the authoritative row, not part of identity.
    """

    shop_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    feature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    activation: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state_token: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "feature_id",
            name="uq_ad_control_shop_feature_identity",
        ),
        Index("ix_ad_control_shop_feature_lookup", "shop_id", "feature_id"),
    )


class AdControlCampaignFeatureRow(BaseTable):
    """
    Campaign-level authority row (OVERRIDE or DISABLED only).

    Logical identity: ``(shop_id, advert_id, feature_id)``.
    INHERIT is represented by row **absence**.
    """

    shop_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    advert_id: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state_token: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "advert_id",
            "feature_id",
            name="uq_ad_control_campaign_feature_identity",
        ),
        Index(
            "ix_ad_control_campaign_feature_lookup",
            "shop_id",
            "advert_id",
            "feature_id",
        ),
    )
