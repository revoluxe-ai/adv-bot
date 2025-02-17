from sqlalchemy import func
from app.modules.common_slaves.wildberries.models import *
from app.payments.db.models import Payment
from app.utils.db.assoc_tables import favorite_advs_association, user_reflink_association
from app.utils.db.base import BaseTable




class User(BaseTable):
    user_telegram_id = Column(BIGINT, nullable=False, unique=True)
    username = Column(String)
    wb_user_cabinets: Mapped[list['WBUserCabinet']] = relationship("WBUserCabinet", back_populates="user", cascade="all, delete-orphan")
    adv_updater_user_chat_id: Mapped[int] = Column(BIGINT, nullable=True)
    referral_links: Mapped[list['RefLink']] = relationship('RefLink', back_populates='referrer',
                                                           cascade="all, delete-orphan")
    payments: Mapped[list['Payment']] = relationship('Payment', back_populates='user')
    wb_tokens: Mapped[list['WBToken']] = relationship('WBToken', back_populates='user', cascade="all, delete-orphan")
    favorites_advs: Mapped[list['AdvSetting']] = relationship('AdvSetting', secondary=favorite_advs_association)
    __table_args__ = (
        Index('user_telegram_id_index', user_telegram_id),
    )




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

