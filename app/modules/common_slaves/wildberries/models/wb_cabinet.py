import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Index, text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.client_bot.user_interface.states import AdvSetting
from app.modules.common_slaves.wildberries.models.models import WBCategory, WBUserCabinet, WBBonusPayment, \
    WBBalancePayment
from app.utils.db.base import BaseTable
import typing
if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import WBCard

class WBCabinet(BaseTable):
    shop_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    wb_cards: Mapped[list["WBCard"]] = relationship("WBCard", back_populates="wb_cabinet", uselist=True)
    wb_categories: Mapped[list[WBCategory]] = relationship("WBCategory", uselist=True)
    adv_settings: Mapped[list['AdvSetting']] = relationship("AdvSetting", back_populates="wb_cabinet", uselist=True)
    wb_user_cabinets: Mapped[list[WBUserCabinet]] = relationship(
        "WBUserCabinet",
        back_populates="wb_cabinet",
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    expiration_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False,
                                                               server_default=text('datetime("now", "+7 days")'))
    expiration_alarm_days_pass: Mapped[int | None] = mapped_column(Integer, default=None)
    demo: Mapped[bool] = mapped_column(Boolean, default=True)
    balance: Mapped[float] = mapped_column(Float, default=0, server_default=text("0"), nullable=False)
    bonus: Mapped[float] = mapped_column(Float, default=0, server_default=text("0"), nullable=False)
    white_list_update_active: Mapped[bool] = mapped_column(Boolean, default=False)
    balance_payments: Mapped[list['WBBalancePayment']] = relationship("WBBalancePayment", back_populates="wb_cabinet",
                                                                    uselist=True)
    bonus_payments: Mapped[list['WBBonusPayment']] = relationship("WBBonusPayment", back_populates="wb_cabinet",
                                                                uselist=True)
    __table_args__ = (
        Index("idx_balance_bonus", "balance", "bonus"),
        Index("idx_balance", "balance"),
        Index("idx_bonus", "bonus"),
        Index("idx_wb_cabinet_id", "id"),
    )

    @hybrid_property
    def calculated_balance(self) -> float:
        """Вычисляет баланс на основе начального значения balance и всех платежей"""
        if not self.balance_payments:
            return float(self.balance)
        return float(self.balance + sum(float(payment.amount) for payment in self.balance_payments))

    @hybrid_property
    def calculated_bonus(self) -> float:
        """Вычисляет бонусы на основе начального значения bonus и всех платежей"""
        if not self.bonus_payments:
            return float(self.bonus)
        return float(self.bonus + sum(float(payment.amount) for payment in self.bonus_payments))

