import json
from typing import cast
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.common_slaves.wildberries.models.adv_setting import AdvSetting
from app.modules.common_slaves.wildberries.models.models import WBCategory
from app.utils.db.base import BaseTable

class WBCard(BaseTable):
    nmid: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    offer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    wb_category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wbcategory.id"), nullable=True)
    wb_category: Mapped["WBCategory"] = relationship("WBCategory", back_populates="wb_cards", lazy="joined")
    json: Mapped[str] = mapped_column(JSONB)
    wb_cabinet_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=True)
    wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet", back_populates="wb_cards")
    adv_setting_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("advsetting.id"), nullable=True)
    adv_setting: Mapped["AdvSetting"] = relationship("AdvSetting", back_populates="wb_cards")
    updated: Mapped[bool] = mapped_column(Boolean, default=False)
    add_to_db: Mapped[bool] = mapped_column(Boolean, default=False)

    @hybrid_property
    def card_json(self) -> dict[str, object]:
        data = json.loads(self.json)
        if isinstance(data, dict):
            return cast(dict[str, object], data)
        return {}

    @property
    def brand(self) -> str:
        brand = self.card_json.get("brand", "")
        if isinstance(brand, str):
            return brand
        return str(brand)

    @property
    def photos(self) -> list[str]:
        raw = self.card_json.get("photos")
        if not isinstance(raw, list):
            return []
        urls: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                val = item.get("big")
                if isinstance(val, str):
                    urls.append(val)
                else:
                    urls.append(str(val))
        return urls

    @property
    def SubjectId(self) -> int | None:
        subject_id = self.card_json.get("subjectID")
        if isinstance(subject_id, int) or subject_id is None:
            return subject_id
        if isinstance(subject_id, str) and subject_id.isdigit():
            return int(subject_id)
        return None

