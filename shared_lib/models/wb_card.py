from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base_table import BaseTable

class WBCard(BaseTable):
    nmid = Column(Integer, unique=True, nullable=False)
    offer_id = Column(String)
    name = Column(String)
    wb_category_id = Column(Integer, ForeignKey("wbcategory.id"))
    wb_category = relationship("WBCategory", back_populates="wb_cards", lazy="joined")
    json = Column(JSONB)
    wb_cabinet_id = Column(Integer, ForeignKey("wbcabinet.id"))
    wb_cabinet = relationship("WBCabinet", back_populates="wb_cards")
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"))
    adv_setting = relationship("AdvSetting", back_populates="wb_cards")
    updated = Column(Boolean, default=False)
    add_to_db = Column(Boolean, default=False)

