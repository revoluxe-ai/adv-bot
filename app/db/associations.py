
from sqlalchemy import (Column, Integer, String, ForeignKey,
                        BIGINT, Boolean, select, Float, DateTime, Table)
from sqlalchemy.orm import relationship, sessionmaker, Mapped

from .base import BaseTable
from ..telegram_bot.models import User


class WBUserCabinet(BaseTable):
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'))
    wb_cabinet = relationship("WBCabinet", back_populates="wb_user_cabinets",
                              lazy='joined')
    user_id = Column(Integer, ForeignKey('user.id'))
    user: Mapped[User]  = relationship("User", back_populates="wb_user_cabinets",
                        lazy='joined')
    name = Column(String(255), nullable=False)








