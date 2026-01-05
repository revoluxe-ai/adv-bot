from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class BillingEvent(BaseTable):
    __tablename__ = "billing_event"  # pyright: ignore

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )
    user_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    wb_cabinet_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=True
    )
    shop_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    bonus_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="RUB")
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_billing_event_created_at", "created_at"),
        Index("idx_billing_event_type_created_at", "event_type", "created_at"),
        Index(
            "idx_billing_event_user_telegram_created_at",
            "user_telegram_id",
            "created_at",
        ),
        Index("idx_billing_event_wb_cabinet_created_at", "wb_cabinet_id", "created_at"),
        Index("idx_billing_event_correlation_id", "correlation_id"),
        Index("idx_billing_event_shop_id", "shop_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<BillingEvent(id={self.id}, event_type={self.event_type}, "
            f"source={self.source}, user={self.user_id}, wb_cabinet={self.wb_cabinet_id})>"
        )
