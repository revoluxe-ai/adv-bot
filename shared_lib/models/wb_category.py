from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base_table import BaseTable

class WBCategory(BaseTable):
    cabinet_id = Column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet = relationship("WBCabinet", back_populates="wb_categories")
    wb_category_name = Column(String, nullable=False)
    wb_cards = relationship("WBCard", back_populates="wb_category", uselist=True)
    __table_args__ = (
        Index("ix_wb_category_name", "wb_category_name"),
    )

