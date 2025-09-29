from shared_lib.models.base_table import BaseTable
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BIGINT, String, Index
from shared_lib.models.favorite_advs_association import favorite_advs_association
from shared_lib.models.wbusercabinet import WBUserCabinet
from shared_lib.models.reflink import RefLink
from shared_lib.models.wbtoken import WBToken


class User(BaseTable):
    # TODO Модель расшарена, отрефакторить перед изменениями
    user_telegram_id: Mapped[int] = mapped_column(BIGINT, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    wb_user_cabinets: Mapped[list[WBUserCabinet]] = relationship(
        "WBUserCabinet", back_populates="user", cascade="all, delete-orphan"
    )
    adv_updater_user_chat_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    referral_links: Mapped[list[RefLink]] = relationship(
        "RefLink", back_populates="referrer", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user")
    wb_tokens: Mapped[list[WBToken]] = relationship(
        "WBToken", back_populates="user", cascade="all, delete-orphan"
    )
    favorites_advs: Mapped[list["AdvSetting"]] = relationship(
        "AdvSetting", secondary=favorite_advs_association
    )
    __table_args__ = (Index("user_telegram_id_index", user_telegram_id),)
