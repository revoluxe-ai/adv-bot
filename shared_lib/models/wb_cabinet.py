from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime, text, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base_table import BaseTable

class WBCabinet(BaseTable):
    __tablename__ = "wbcabinet"
    id = Column(Integer, primary_key=True)
    shop_id = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True)
    expiration_time = Column(DateTime, nullable=False, server_default=text('datetime("now", "+7 days")'))
    expiration_alarm_days_pass = Column(Integer, default=None)
    demo = Column(Boolean, default=True)
    balance = Column(Float, default=0, server_default=text("0"), nullable=False)
    bonus = Column(Float, default=0, server_default=text("0"), nullable=False)
    white_list_update_active = Column(Boolean, default=False)
    adv_settings = relationship(
        "AdvSetting", back_populates="wb_cabinet", uselist=True
    )
    wb_cards = relationship("WBCard", back_populates="wb_cabinet", uselist=True)
    wb_categories = relationship("WBCategory", back_populates="wb_cabinet", uselist=True)
    balance_payments = relationship("WBBalancePayment", back_populates="wb_cabinet", uselist=True)
    bonus_payments = relationship("WBBonusPayment", back_populates="wb_cabinet", uselist=True)
    wb_user_cabinets = relationship("WBUserCabinet", back_populates="wb_cabinet", uselist=True)
    __table_args__ = (
        Index("idx_balance_bonus", "balance", "bonus"),
        Index("idx_balance", "balance"),
        Index("idx_bonus", "bonus"),
        Index("idx_wb_cabinet_id", "id"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def calculated_balance(self) -> float:
        if not self.balance_payments:
            return self.balance
        return self.balance + sum(payment.amount for payment in self.balance_payments)

    @property
    def calculated_bonus(self) -> float:
        if not self.bonus_payments:
            return self.bonus
        return self.bonus + sum(payment.amount for payment in self.bonus_payments)
