from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from .base_table import BaseTable

class KeywordSetting(BaseTable):
    text = Column(String, nullable=False)
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"))
    adv_setting = relationship("AdvSetting", back_populates="keyword_settings", uselist=False)
    predict_ctr = Column(Float, nullable=True)
    adv_keywords = relationship(
        "AdvKeyword",
        back_populates="keyword_setting",
        cascade="all, delete-orphan",
        uselist=True,
    )
    hard_status = Column(Integer, default=1)
    added_clicks = Column(Integer, default=0)
    added_views = Column(Integer, default=0)
    auto_block = Column(Boolean)
    relevant = Column(Boolean, nullable=True, default=False)
    __table_args__ = (
        UniqueConstraint("text", "adv_setting_id"),
        Index("ix_text_adv_setting_id", "text", "adv_setting_id"),
        Index("ix_keywordsetting_status_adv", "hard_status", "adv_setting_id"),
        Index("ix_keywordsetting_adv_setting_id", "adv_setting_id"),
        Index("ix_keywordsetting_text", "text"),
    )

