from __future__ import annotations

import typing
from datetime import date
from enum import StrEnum

from sqlalchemy import Integer, Date, ForeignKey, String, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.db.base import BaseTable

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


class AdvPaymentLegType(StrEnum):
    """Тип слота в AdvPayment (fair leg-pause billing)."""

    AUTO_LEG = "auto_leg"
    SEARCH_LEG = "search_leg"


class AdvPayment(BaseTable):
    __tablename__ = "advpayment"  # pyright: ignore[reportAssignmentType]
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    adv_setting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("advsetting.id"), nullable=False
    )
    adv_setting: Mapped["AdvSetting"] = relationship(
        "AdvSetting",
        back_populates="payments",
        uselist=False,
    )
    type: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    __table_args__ = (
        UniqueConstraint(
            "date", "adv_setting_id", "type", name="uix_date_adv_setting_id_type"
        ),
    )
