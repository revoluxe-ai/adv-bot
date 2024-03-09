
from sqlalchemy import (Column, Integer, String, ForeignKey,
                        BIGINT, Boolean, select, Float, DateTime, Table)
from sqlalchemy.orm import relationship, sessionmaker


from .base import BaseTable


class WBUserCabinet(BaseTable):
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'))
    wb_cabinet = relationship("WBCabinet", back_populates="wb_user_cabinets",
                              lazy='joined')
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("User", back_populates="wb_user_cabinets",
                        lazy='joined')
    name = Column(String(255), nullable=False)








