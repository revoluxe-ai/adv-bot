from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    adv_id = Column(Integer, nullable=False, )
    date = Column(DateTime, nullable=False)
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'), nullable=False)
    adv_setting = relationship('AdvSetting', back_populates='payments')
