from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BIGINT, ForeignKey
from shared_lib.models.base_table import BaseTable

class WBUserCabinet(BaseTable):
    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey('user.id'))
    wb_cabinet_id: Mapped[int] = mapped_column(BIGINT, ForeignKey('wbcabinet.id'))
    user = relationship("User", back_populates="wb_user_cabinets")
    wb_cabinet = relationship("WBCabinet", back_populates="wb_user_cabinets")

