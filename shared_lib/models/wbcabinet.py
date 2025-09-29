from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from shared_lib.models.base_table import BaseTable
from shared_lib.models.user import User
from shared_lib.models.favorite_advs_association import favorite_advs_association
from shared_lib.models.wbusercabinet import WBUserCabinet
from app_old.modules.common_slaves.wildberries.models.models import WBCategory, WBCard

class WBCabinet(BaseTable):
    shop_id: Mapped[str] = Column(String, nullable=False, unique=True)
    wb_cards: Mapped[list["WBCard"]] = relationship("WBCard", back_populates="wb_cabinet", uselist=True)
    wb_categories = relationship("WBCategory", uselist=True)
    adv_settings = relationship("AdvSetting", back_populates="wb_cabinet", uselist=True)
    wb_user_cabinets: Mapped[list[WBUserCabinet]] = relationship(
        "WBUserCabinet",
        back_populates="wb_cabinet",
    )
    active = Column(Boolean, default=True)
    expiration_time = Column(DateTime, nullable=False, server_default=text('datetime("now", "+7 days")'))
    expiration_alarm_days_pass = Column(Integer, default=None)
    demo: Mapped[bool] = Column(Boolean, default=True)
    balance = mapped_column(Float, default=0, server_default=text("0"), nullable=False)
    bonus: Mapped[float] = mapped_column(Float, default=0, server_default=text("0"), nullable=False)
    white_list_update_active = Column(Boolean, default=False)
    balance_payments = relationship("WBBalancePayment", back_populates="wb_cabinet", uselist=True)
    bonus_payments = relationship("WBBonusPayment", back_populates="wb_cabinet", uselist=True)
    __table_args__ = (
        Index("idx_balance_bonus", "balance", "bonus"),
        Index("idx_balance", "balance"),
        Index("idx_bonus", "bonus"),
        Index("idx_wb_cabinet_id", "id"),
    )

    @hybrid_property
    def calculated_balance(self) -> float:
        if not self.balance_payments:
            return float(self.balance)
        return float(self.balance + sum(float(payment.amount) for payment in self.balance_payments))

    @hybrid_property
    def calculated_bonus(self) -> float:
        if not self.bonus_payments:
            return float(self.bonus)
        return float(self.bonus + sum(float(payment.amount) for payment in self.bonus_payments))
