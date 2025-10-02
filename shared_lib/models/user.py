from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base_table import BaseTable

class User(BaseTable):
    user_telegram_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    wb_user_cabinets: Mapped[list["WBUserCabinet"]] = relationship(
        "WBUserCabinet", back_populates="user", cascade="all, delete-orphan"
    )
    wb_tokens: Mapped[list["WBToken"]] = relationship(
        "WBToken", back_populates="user", cascade="all, delete-orphan"
    )
    favorites_advs: Mapped[list["AdvSetting"]] = relationship(
        "AdvSetting", secondary="favorite_advs_association"
    )

    __table_args__ = (Index("user_telegram_id_index", user_telegram_id),)

