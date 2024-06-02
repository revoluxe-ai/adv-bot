from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

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
