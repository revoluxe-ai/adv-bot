from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base_table import BaseTable

class WBUserCabinet(BaseTable):
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet", back_populates="wb_user_cabinets")
    user_id: Mapped[int] = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="wb_user_cabinets")
    name = Column(String(255), nullable=False)
    __table_args__ = (
        UniqueConstraint("wb_cabinet_id", "user_id", name="_wb_cabinet_id_user_id_uc"),
        Index("idx_wb_user_cabinet_user_id", "user_id"),
        Index("idx_wb_user_cabinet_cabinet_id", "wb_cabinet_id"),
    )

