from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BIGINT, ForeignKey, String
from shared_lib.models.base_table import BaseTable

class WBToken(BaseTable):
    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey('user.id'))
    token: Mapped[str] = mapped_column(String, nullable=False)
    user = relationship("User", back_populates="wb_tokens")

