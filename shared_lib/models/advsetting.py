import re
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import BIGINT
from .base_table import BaseTable


class AdvSetting(BaseTable):
    adv_id = Column(BIGINT(), unique=True, nullable=True)
    name = Column(String, nullable=False)
    bot_active = Column(Boolean, default=False)
    nmids = Column(JSONB, default=[])
    type = Column(Integer, nullable=True)
    pass_days = Column(Integer, default=30)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"AdvSetting(adv_id={self.adv_id}, bot_active={self.bot_active})"

    _search_adv_id = Column(Integer, nullable=True)

    @property
    def search_adv_id(self) -> int | None:  # Аукцион
        if self._search_adv_id is not None:
            return int(self._search_adv_id)
        if not self.name:
            return None
        name = self.name.replace(" ", "")
        pattern = re.compile(r"<!-\[(\d+)\]-!>")
        match = re.search(pattern, name)
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    @search_adv_id.setter
    def search_adv_id(self, value: int) -> None:
        self._search_adv_id = value
