# Модель AdvSetting перенесена из shared_lib/models/adv_setting.py
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, text
from sqlalchemy.dialects.postgresql import BIGINT, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base_table import BaseTable  # предполагается, что BaseTable есть в dto/base_table.py

class AdvSetting(BaseTable):
    adv_id: Mapped[int] = mapped_column(BIGINT(), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    # wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet", back_populates="adv_settings", lazy="joined")
    # wb_cards: Mapped[list] = relationship("WBCard", back_populates="adv_setting", cascade="all,delete-orphan", uselist=True)
    active_status: Mapped[str] = mapped_column(String, default=False)
    # adv_keywords: Mapped[list] = relationship("AdvKeyword", cascade="all, delete-orphan", back_populates="adv_setting", uselist=True)
    bot_active: Mapped[bool] = mapped_column(Boolean, default=False)
    nmids: Mapped[list[int]] = mapped_column(JSONB, default=[])
    # keyword_settings: Mapped[list] = relationship("KeywordSetting", cascade="all, delete-orphan", back_populates="adv_setting", uselist=True)
    pass_days: Mapped[int] = mapped_column(Integer, default=30)
    boost: Mapped[float] = mapped_column(Float, server_default=text("1"))
    type: Mapped[int] = mapped_column(Integer, nullable=True)
    hard_min_ctr: Mapped[float] = mapped_column(Float)
