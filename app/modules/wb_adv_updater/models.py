from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.db.base import BaseTable

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


Base = declarative_base()


class ItemFeature(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    nmid = Column(Integer, nullable=False, unique=True)
    vector = Column(JSONB, nullable=False)


class KeywordFeature(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = Column(String, nullable=False, unique=True)
    vector = Column(JSONB, nullable=False)


class GlobalCategorySetting(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, nullable=False, unique=True)
    min_ctr = Column(Float, nullable=False)


class AdvPayment(BaseTable):
    __tablename__ = "advpayment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"), nullable=False)
    adv_setting: Mapped[list["AdvSetting"]] = relationship("AdvSetting", back_populates="payments")
    type = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    __table_args__ = (UniqueConstraint("date", "adv_setting_id", "type", name="uix_date_adv_setting_id_type"),)
