import json
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from shared_lib.models.base_table import BaseTable
from shared_lib.models.wbcabinet import WBCabinet

class WBCard(BaseTable):
    nmid: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    offer_id = Column(String)
    name = Column(String)
    wb_category_id = Column(Integer, ForeignKey("wbcategory.id"))
    wb_category = relationship("WBCategory", back_populates="wb_cards", lazy="joined")
    json: Mapped[str] = Column(JSONB)
    wb_cabinet_id = Column(Integer, ForeignKey("wbcabinet.id"))
    wb_cabinet: Mapped[WBCabinet] = relationship("WBCabinet", back_populates="wb_cards")
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"))
    adv_setting = relationship("AdvSetting", back_populates="wb_cards")  # Используем строку для связи
    updated = Column(Boolean, default=False)
    add_to_db = Column(Boolean, default=False)

    @hybrid_property
    def card_json(self) -> dict[str, object]:
        return json.loads(self.json)

    @property
    def brand(self) -> str:
        value = self.card_json.get("brand")
        return str(value) if value is not None else ""

    @property
    def photos(self) -> list[str]:
        photos = self.card_json.get("photos", [])
        urls: list[str] = []
        for photo in photos:
            url = photo.get("big", "")
            urls.append(str(url))
        return urls

    @property
    def SubjectId(self) -> int:
        value = self.card_json.get("subjectID")
        return int(value) if value is not None else 0
