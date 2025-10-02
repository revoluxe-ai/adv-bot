# Модель AdvSetting перенесена из shared_lib/models/adv_setting.py
from sqlalchemy import Integer, String, Boolean, Float, ForeignKey, text
from sqlalchemy.dialects.postgresql import BIGINT, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base_table import BaseTable  # предполагается, что BaseTable есть в dto/base_table.py
import re


class AdvSetting(BaseTable):
    adv_id: Mapped[int] = mapped_column(BIGINT(), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    active_status: Mapped[str] = mapped_column(String, default=False)
    bot_active: Mapped[bool] = mapped_column(Boolean, default=False)
    nmids: Mapped[list[int]] = mapped_column(JSONB, default=[])
    pass_days: Mapped[int] = mapped_column(Integer, default=30)
    boost: Mapped[float] = mapped_column(Float, server_default=text("1"))
    type: Mapped[int] = mapped_column(Integer, nullable=True)
    hard_min_ctr: Mapped[float] = mapped_column(Float)
    _search_adv_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def search_adv_id(self) -> int | None:
        if self._search_adv_id:
            return self._search_adv_id
        if not self.name:
            return None
        name = self.name.replace(" ", "")
        pattern = re.compile(r"<!-\[(\d+)\]-!>")
        match = re.search(pattern, name)
        if not match:
            return None
        else:
            return int(match.group(1))

    @search_adv_id.setter
    def search_adv_id(self, value: int):
        assert isinstance(value, int)
        self._search_adv_id = value
