from sqlalchemy import BIGINT, Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship, Mapped

from app.utils.db.base import BaseTable
from app.utils.db.models import User


class Payment(BaseTable):
    user: Mapped["User"] = relationship("User", back_populates="payments")
    user_id = Column(BIGINT, ForeignKey("user.id"))
    amount = Column(BIGINT, nullable=False)
    target = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=True, server_default=func.now())
