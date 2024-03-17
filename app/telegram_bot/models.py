import json
import datetime
from sqlalchemy import (Column, Integer, String, ForeignKey,
                        BIGINT, Boolean, select, Float, DateTime, Table)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, sessionmaker, Mapped
from typing import TYPE_CHECKING
from app.db.base import BaseTable

if TYPE_CHECKING:
    from app.db.associations import WBUserCabinet
    from app.wildberries.models import WBToken



class User(BaseTable):
    user_telegram_id = Column(BIGINT, nullable=False, unique=True)
    username = Column(String)
    wb_tokens: Mapped[list['WBToken']] = relationship('WBToken',
                             back_populates='user')
    wb_user_cabinets: Mapped[list['WBUserCabinet']] = relationship("WBUserCabinet", back_populates="user",)











