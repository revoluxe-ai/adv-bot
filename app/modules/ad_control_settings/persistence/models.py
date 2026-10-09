"""ORM rows configured hierarchical ad control (shop + campaign scopes)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class AdControlShopFeatureRow(BaseTable):
    """
    Shop-level feature slot: activation + optional typed payload.

    Identity: ``(shop_id, feature_id, schema_version)``.
    """

    shop_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    feature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    activation: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    state_token: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "feature_id",
            "schema_version",
            name="uq_ad_control_shop_feature_identity",
        ),
        Index("ix_ad_control_shop_feature_lookup", "shop_id", "feature_id"),
    )


class AdControlCampaignFeatureRow(BaseTable):
    """
    Campaign-level feature slot: mode + optional override payload.

    Authority: ``(shop_id, advert_id)`` + ``(feature_id, schema_version)``.
    """

    shop_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    advert_id: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
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
            "schema_version",
            name="uq_ad_control_campaign_feature_identity",
        ),
        Index(
            "ix_ad_control_campaign_feature_lookup",
            "shop_id",
            "advert_id",
            "feature_id",
        ),
    )
