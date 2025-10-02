from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base_table import BaseTable

class AdvKeyword(BaseTable):
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"), nullable=False)
    adv_setting = relationship("AdvSetting", back_populates="adv_keywords")
    text = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    positive = Column(Boolean)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0)
    add_to_db = Column(Boolean, default=False)
    keyword_setting_id = Column(Integer, ForeignKey("keywordsetting.id"), nullable=False)
    keyword_setting = relationship("KeywordSetting", back_populates="adv_keywords")
    __table_args__ = (UniqueConstraint("text", "date", "adv_setting_id", name="_text_date_adv_setting_id_uc"),)

