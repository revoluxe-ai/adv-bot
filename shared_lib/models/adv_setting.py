# Модель AdvSetting перенесена из app/modules/common_slaves/wildberries/models/models.py
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, text
from sqlalchemy.dialects.postgresql import BIGINT, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base_table import BaseTable

class AdvSetting(BaseTable):
    # ...перенесённые поля и связи...
    adv_id: Mapped[int] = mapped_column(
        BIGINT(),
        unique=True,
        nullable=True,
    )
    name = mapped_column(String, nullable=False)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet", back_populates="adv_settings", lazy="joined")
    wb_cards: Mapped[list] = relationship(
        "WBCard",
        back_populates="adv_setting",
        cascade="all,delete-orphan",
        uselist=True,
    )
    active_status: Mapped[str] = mapped_column(String, default=False)
    adv_keywords: Mapped[list] = relationship(
        "AdvKeyword",
        cascade="all, delete-orphan",
        back_populates="adv_setting",
        uselist=True,
    )
    bot_active: Mapped[bool] = mapped_column(Boolean, default=False)
    nmids: Mapped[list[int]] = mapped_column(JSONB, default=[])
    keyword_settings: Mapped[list] = relationship(
        "KeywordSetting",
        cascade="all, delete-orphan",
        back_populates="adv_setting",
        uselist=True,
    )
    pass_days = Column(Integer, default=30)
    boost = Column(Float, server_default=text("1"))
    type: Mapped[int] = Column(Integer, nullable=True)
    hard_min_ctr = Column(Float)
    # ...другие поля и методы по необходимости...
