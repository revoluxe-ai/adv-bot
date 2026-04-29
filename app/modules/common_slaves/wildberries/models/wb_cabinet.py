from __future__ import annotations

import datetime
import typing

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.settings import settings
from app.utils.db.base import BaseTable

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models.models import (
        AdvSetting,
        WBBalancePayment,
        WBBonusPayment,
        WBCard,
        WBCategory,
        WBUserCabinet,
    )


class WBCabinet(BaseTable):
    shop_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    wb_cards: Mapped[list[WBCard]] = relationship(
        "WBCard", back_populates="wb_cabinet", uselist=True
    )
    wb_categories: Mapped[list[WBCategory]] = relationship("WBCategory", uselist=True)
    adv_settings: Mapped[list[AdvSetting]] = relationship(
        "AdvSetting", back_populates="wb_cabinet", uselist=True
    )
    wb_user_cabinets: Mapped[list[WBUserCabinet]] = relationship(
        "WBUserCabinet",
        back_populates="wb_cabinet",
    )
    active: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    expiration_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now() + interval '7 days'")
    )
    expiration_alarm_days_pass: Mapped[int | None] = mapped_column(
        Integer, default=None
    )
    demo: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    balance: Mapped[float] = mapped_column(
        Float, default=0, server_default=text("0"), nullable=False
    )
    bonus: Mapped[float] = mapped_column(
        Float, default=0, server_default=text("0"), nullable=False
    )
    balance_payments: Mapped[list[WBBalancePayment]] = relationship(
        "WBBalancePayment", back_populates="wb_cabinet", uselist=True
    )
    bonus_payments: Mapped[list[WBBonusPayment]] = relationship(
        "WBBonusPayment", back_populates="wb_cabinet", uselist=True
    )
    default_max_cpm: Mapped[int] = mapped_column(Integer,
                                                 nullable=False,
                                                 default=settings.DEFAULT_MAX_CPM,
                                                 server_default=text(str(settings.DEFAULT_MAX_CPM)))
    balance_went_negative_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        Index("idx_balance_bonus", "balance", "bonus"),
        Index("idx_balance", "balance"),
        Index("idx_bonus", "bonus"),
        Index("idx_wb_cabinet_id", "id"),
        Index('idx_shop_id_active', 'shop_id','active'),
    )

    @hybrid_property
    def calculated_balance(self) -> float:
        """Вычисляет баланс на основе начального значения balance и всех платежей"""
        if not self.balance_payments:
            return float(self.balance)
        return float(
            self.balance
            + sum(float(payment.amount) for payment in self.balance_payments)
        )

    @calculated_balance.expression
    def calculated_balance(cls):
        # В контексте SQLAlchemy вернём простое выражение по колонке balance.
        # Это предотвращает попытки интерпретации Python-итераторов при доступе к
        # атрибутам класса (например, при MagicMock(spec=...)).
        return cls.balance

    @hybrid_property
    def calculated_bonus(self) -> float:
        """Вычисляет бонусы на основе начального значения bonus и всех платежей"""
        if not self.bonus_payments:
            return float(self.bonus)
        return float(
            self.bonus + sum(float(payment.amount) for payment in self.bonus_payments)
        )

    @calculated_bonus.expression
    def calculated_bonus(cls):
        # Аналогично — возвращаем колонку bonus в качестве SQL-выражения.
        return cls.bonus
