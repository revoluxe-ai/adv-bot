from sqlalchemy import Column, Integer, Float, String, DateTime, Index, text, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base_table import BaseTable

class WBBalancePayment(BaseTable):
    __tablename__ = "wbbalancepayment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet = relationship("WBCabinet", back_populates="balance_payments")

    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    transaction_date_time = Column(DateTime, nullable=False, server_default=text("now()"))
    operation_type = Column(String, nullable=False, server_default=text("'subtract'"))

    __table_args__ = (
        Index("idx_wb_balance_payment_cabinet_id", "wb_cabinet_id"),
        Index("idx_wb_balance_payment_date", "transaction_date_time"),
        Index("idx_wb_balance_payment_operation", "operation_type"),
    )


class WBBonusPayment(BaseTable):
    __tablename__ = "wbbonuspayment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet = relationship("WBCabinet", back_populates="bonus_payments")

    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    transaction_date_time = Column(DateTime, nullable=False, server_default=text("now()"))

    __table_args__ = (
        Index("idx_wb_bonus_payment_cabinet_id", "wb_cabinet_id"),
    )
