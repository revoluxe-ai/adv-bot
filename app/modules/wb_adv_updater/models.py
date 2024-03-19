from sqlalchemy import (Column, Integer, String, Float)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from app.utils.db.base import BaseTable

Base = declarative_base()


class ItemFeature(Base):
    __tablename__ = 'item_features'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nmid = Column(Integer, nullable=False, unique=True)
    vector = Column(JSONB, nullable=False)



class KeywordFeature(Base):
    __tablename__ = 'keyword_features'
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String, nullable=False, unique=True)
    vector = Column(JSONB, nullable=False)



class GlobalCategorySetting(BaseTable):
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, nullable=False, unique=True)
    min_ctr = Column(Float, nullable=False)