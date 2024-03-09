import json
import datetime
from sqlalchemy import (Column, Integer, String, ForeignKey,
                        BIGINT, Boolean, select, Float, DateTime, Table)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, sessionmaker
from app.db.base import BaseTable



class User(BaseTable):
    user_telegram_id = Column(Integer, nullable=False, unique=True)
    username = Column(String)
    wb_tokens = relationship('WBToken',
                             back_populates='user',
                             lazy='joined',
                             uselist=True)
    wb_user_cabinets = relationship("WBUserCabinet", back_populates="user",
                                    uselist=True,
                                    lazy='joined')











