from sqlalchemy import BIGINT, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.utils.db.base import BaseTable


class Payment(BaseTable):
    user = relationship('User', back_populates='payments')
    user_id = Column(BIGINT, ForeignKey('user.id'))
    amount = Column(BIGINT, nullable=False)
    target = Column(String, nullable=False)
