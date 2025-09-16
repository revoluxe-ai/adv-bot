from sqlalchemy import Table, Column, BIGINT, ForeignKey

from app.utils.db.base import Base


user_reflink_association = Table(
    'user_reflink_association', Base.metadata,
    Column('user_id', BIGINT, ForeignKey('user.id'), primary_key=True),
    Column('reflink_id', BIGINT, ForeignKey('reflink.id'), primary_key=True)
)



favorite_advs_association = Table(
    'favorite_advs_association', Base.metadata,
    Column('user_id', BIGINT, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    Column('adv_id', BIGINT, ForeignKey('advsetting.id', ondelete='CASCADE'), primary_key=True)
)
