from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.db.base import BaseTable

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
    from app.utils.db.models import User


class BalanceReminder(BaseTable):
    """
    Таблица для хранения статусов отправки напоминаний о балансе.
    Обеспечивает идемпотентность (не спамить) и очередь отправки (status).
    """

    wb_cabinet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "wb_cabinet_id",
            "user_id",
            "day",
            "level",
            name="uq_balance_reminders",
        ),
        Index("idx_balance_reminders_send", "status", "day", "user_id"),
    )
