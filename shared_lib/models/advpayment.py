from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from shared_lib.models.base_table import BaseTable

class AdvPayment(BaseTable):
    __tablename__ = "advpayment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"), nullable=False)
    adv_setting: Mapped[list["AdvSetting"]] = relationship("AdvSetting", back_populates="payments")
    type = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    __table_args__ = (
        UniqueConstraint("date", "adv_setting_id", "type", name="uix_date_adv_setting_id_type"),
    )
