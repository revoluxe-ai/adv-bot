from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey, UniqueConstraint, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, mapped_column

from app.utils.db.base import BaseTable

Base = declarative_base()


class ItemFeature(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    nmid = Column(Integer, nullable=False, unique=True)
    vector = Column(JSONB, nullable=False)



class KeywordFeature(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String, nullable=False, unique=True)
    vector = Column(JSONB, nullable=False)



class GlobalCategorySetting(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, nullable=False, unique=True)
    min_ctr = Column(Float, nullable=False)


class AdvPayment(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'), nullable=False)
    adv_setting = relationship('AdvSetting', back_populates='payments')
    __table_args__ = (
        UniqueConstraint('date', 'adv_setting_id', 'type', name='uix_date_adv_setting_id_type'),
    )
    type = mapped_column(String, nullable=True)