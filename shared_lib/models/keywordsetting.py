import json
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from shared_lib.models.base_table import BaseTable

class KeywordSetting(BaseTable):
    """hard_status
    0 - black listA
    1 - in test
    2 - white list
    """
    text = Column(String, nullable=False)
    adv_setting_id: Mapped[int] = mapped_column(ForeignKey("advsetting.id"))
    adv_setting: Mapped["AdvSetting"] = relationship("AdvSetting", back_populates="keyword_settings", uselist=False)
    predict_ctr = Column(Float, nullable=True)
    adv_keywords = relationship(
        "AdvKeyword",
        back_populates="keyword_setting",
        cascade="all, delete-orphan",
        uselist=True,
    )
    hard_status: Mapped[int] = mapped_column(Integer, default=1)
    added_clicks = Column(Integer, default=0)
    added_views = Column(Integer, default=0)
    auto_block = Column(Boolean)
    relevant: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False, server_default="false")
    __table_args__ = (
        UniqueConstraint("text", "adv_setting_id"),
        Index("ix_text_adv_setting_id", "text", "adv_setting_id"),
        Index("ix_keywordsetting_status_adv", "hard_status", "adv_setting_id"),
        Index("ix_keywordsetting_adv_setting_id", "adv_setting_id"),
        Index("ix_keywordsetting_text", "text"),
    )

    def to_json(self) -> dict[str, int | str | float | bool | None]:
        return {
            "id": self.id,
            "text": self.text,
            "adv_setting_id": self.adv_setting_id,
            "predict_ctr": self.predict_ctr,
            "hard_status": self.hard_status,
            "added_clicks": self.added_clicks,
            "added_views": self.added_views,
            "auto_block": self.auto_block,
        }

    @classmethod
    def from_json(cls, data: dict[str, int | str | float | bool | None]) -> "KeywordSetting":
        """Создает объект KeywordSetting из JSON данных"""
        if isinstance(data, str):
            data = json.loads(data)
        return cls(
            id=data.get("id"),
            text=data.get("text"),
            adv_setting_id=data.get("adv_setting_id"),
            predict_ctr=data.get("predict_ctr"),
            hard_status=data.get("hard_status"),
            added_clicks=data.get("added_clicks"),
            added_views=data.get("added_views"),
            auto_block=data.get("auto_block"),
        )
