from shared_lib.models.base_table import BaseTable
from sqlalchemy.orm import relationship
from sqlalchemy import Column, BIGINT, ForeignKey, String, DateTime, func


class Payment(BaseTable):
    user = relationship("User", back_populates="payments")
    user_id = Column(BIGINT, ForeignKey("user.id"))
    amount = Column(BIGINT, nullable=False)
    target = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=True, server_default=func.now())
