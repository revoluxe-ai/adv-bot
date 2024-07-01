from sqlalchemy import BIGINT, Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, relationship

from app.modules.common_slaves.wildberries.models import *
from app.payments.db.models import Payment
from app.utils.db.base import Base, BaseTable

user_reflink_association = Table(
    'user_reflink_association', Base.metadata,
    Column('user_id', BIGINT, ForeignKey('user.id'), primary_key=True),
    Column('reflink_id', BIGINT, ForeignKey('reflink.id'), primary_key=True)
)


class User(BaseTable):
    user_telegram_id = Column(BIGINT, nullable=False, unique=True)
    username = Column(String)
    wb_user_cabinets: Mapped[list['WBUserCabinet']] = relationship("WBUserCabinet", back_populates="user", cascade="all, delete-orphan")
    adv_updater_user_chat_id: Mapped[int] = Column(BIGINT, nullable=True)
    referral_links: Mapped[list['RefLink']] = relationship('RefLink', back_populates='referrer',
                                                           cascade="all, delete-orphan")
    payments: Mapped[list['Payment']] = relationship('Payment', back_populates='user')
    wb_tokens: Mapped[list['WBToken']] = relationship('WBToken', back_populates='user', cascade="all, delete-orphan")


class RefLink(BaseTable):
    name = Column(String, nullable=False)
    referrer_id = Column(BIGINT, ForeignKey('user.id'))
    referrer: Mapped['User'] = relationship('User', back_populates='referral_links')
    referred_users: Mapped[list['User']] = relationship(
        'User',
        secondary=user_reflink_association,
        backref='referred_by_links'
    )
    created_at = Column(DateTime, server_default=func.now())
    bonus_code = Column(String, nullable=True)

