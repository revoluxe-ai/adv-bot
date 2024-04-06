from sqlalchemy import Column, BIGINT, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import String
from app.utils.db.base import BaseTable


class User(BaseTable):
    user_telegram_id = Column(BIGINT, nullable=False, unique=True)
    username = Column(String)
    wb_tokens: Mapped[list['WBToken']] = relationship('WBToken', back_populates='user', cascade="all, delete-orphan")
    wb_user_cabinets: Mapped[list['WBUserCabinet']] = relationship("WBUserCabinet", back_populates="user", cascade="all, delete-orphan")
    adv_updater_user_chat_id: Mapped[int] = Column(BIGINT, nullable=True)
    referral_links: Mapped[list['RefLink']] = relationship('RefLink', back_populates='referrer')
    referred_by: Mapped['RefLink'] = relationship('RefLink', back_populates='referrals', nullable=True)


class RefLink(BaseTable):
    name = Column(String, nullable=False)
    referrer_id = Column(BIGINT, ForeignKey('users.id'))
    referrer = relationship('User', back_populates='referral_links')
    referrals = relationship('User', back_populates='referred_by')
    created_at = Column(DateTime, server_default=func.now())

