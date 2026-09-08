"""Журнал фактических списаний промобонусов с кампании (WB GET /adv/v1/upd)."""

from __future__ import annotations

import datetime

from sqlalchemy import (
    BIGINT,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable

__all__ = ["WBCampaignPromoSpend"]


class WBCampaignPromoSpend(BaseTable):
    """Idempotent-журнал строк UPD с paymentType кэшбэк/Keshbek.

    Уменьшает per-campaign promo remaining. Не описывает ordinary spend.
    """

    advert_id: Mapped[int] = mapped_column(
        BIGINT,
        nullable=False,
        comment="WB advertId кампании",
    )
    upd_num: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Номер УПД, если WB его вернул",
    )
    upd_time: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время списания из UPD",
    )
    upd_sum: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Сумма списания промо, ₽",
    )
    payment_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Исходный paymentType WB (Кэшбэк/Keshbek)",
    )
    fingerprint: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Идемпотентный ключ строки UPD",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        server_default=text("now()"),
    )

    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_wbcampaignpromospend_fingerprint"),
        Index("ix_wbcampaignpromospend_advert_id", "advert_id"),
    )
