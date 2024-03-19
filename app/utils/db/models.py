from sqlalchemy import Column, BIGINT
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import String
from app.utils.db.base import BaseTable

class User(BaseTable):
    user_telegram_id = Column(BIGINT, nullable=False, unique=True)
    username = Column(String)
    wb_tokens: Mapped[list['WBToken']] = relationship('WBToken',
                             back_populates='user', cascade="all, delete-orphan")
    wb_user_cabinets: Mapped[list['WBUserCabinet']] = relationship("WBUserCabinet", back_populates="user",
                                                                   cascade="all, delete-orphan")

