from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BIGINT,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy import Enum as SAEnum


from app.utils.db.base import BaseTable

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.shared.domains.wb.enums import (
    AdvType,
)


__all__ = ["WBAutoBudgetTopUp"]


class WBAutoBudgetTopUp(BaseTable):
    """Журнал пополнений бюджета кампаний ботом (для автопополнения)."""

    adv_setting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("advsetting.id"), nullable=False
    )
    adv_setting: Mapped["AdvSetting"] = relationship(
        "AdvSetting", back_populates="auto_budget_topups"
    )
    adv_id: Mapped[int] = mapped_column(
        BIGINT, nullable=False, comment="adv_id кампании, к которой относится пополнение"
    )
    campaign_type: Mapped["AdvType"] = mapped_column(
        SAEnum(
            AdvType,
            name="adv_type_enum",
            validate_strings=True,
        ),
        nullable=False,
        comment="Тип кампании (auto/search)",
    )
    date_msk: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    promo_amount: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Сумма промобонусов в пополнении; credit только при status=success",
    )
    promo_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="percent выбранного WB cashback-пакета",
    )
    promo_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="expiration_date исходного пакета common pool",
    )
    ordinary_amount: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Обычная доля пополнения (amount - promo_amount)",
    )
    balance_type: Mapped[str] = mapped_column(String(32), nullable=False)
    budget_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="started",
        server_default=text("'started'"),
    )
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    __table_args__ = (
        Index(
            "ix_wbautobudgettopup_adv_setting_date",
            "adv_setting_id",
            "date_msk",
        ),
        Index(
            "ix_wbautobudgettopup_adv_campaign",
            "adv_setting_id",
            "adv_id",
            "campaign_type",
            "date_msk",
        ),
    )
