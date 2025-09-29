from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BIGINT, ForeignKey
from shared_lib.models.base_table import BaseTable

class RefLink(BaseTable):
    referrer_id: Mapped[int] = mapped_column(BIGINT, ForeignKey('user.id'))
    referrer = relationship("User", back_populates="referral_links")

