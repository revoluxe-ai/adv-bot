import json
import datetime
from app.my_types import AdvKeyword
from sqlalchemy import (Column, Integer, String, ForeignKey,
                        BIGINT, Boolean, select, Float, DateTime, Table, text, UniqueConstraint)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from ..db.base import BaseTable
from ..wildberries.models import AdvSetting

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

