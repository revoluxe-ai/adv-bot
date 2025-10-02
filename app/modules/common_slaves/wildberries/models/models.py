import datetime
import json
import re
import typing
from dataclasses import dataclass
from enum import Enum
from typing import cast  # добавлено для типизации

import jwt
from jwt import DecodeError
from sqlalchemy import (
    BIGINT,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.wb_api import exceptions
from app.utils.db.base import BaseTable
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

import typing

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet

_sm = get_async_session_maker


class WBUserCabinet(BaseTable):
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet", back_populates="wb_user_cabinets")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped[User] = relationship("User", back_populates="wb_user_cabinets")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    __table_args__ = (
        UniqueConstraint("wb_cabinet_id", "user_id", name="_wb_cabinet_id_user_id_uc"),
        Index("idx_wb_user_cabinet_user_id", "user_id"),
        Index("idx_wb_user_cabinet_cabinet_id", "wb_cabinet_id"),
    )


class WBBalancePayment(BaseTable):
    """Модель для хранения информации о пополнениях баланса"""

    __tablename__ = "wbbalancepayment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet", back_populates="balance_payments")

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    # Тип операции для унификации с бонусами: 'add', 'subtract', 'auto_subtract', 'reset' (если понадобится)
    operation_type: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'subtract'"))
    __table_args__ = (
        Index("idx_wb_balance_payment_cabinet_id", "wb_cabinet_id"),
        Index("idx_wb_balance_payment_date", "transaction_date_time"),
        Index("idx_wb_balance_payment_operation", "operation_type"),
        Index(
            "idx_unique_daily_auto_balance_charge",
            "wb_cabinet_id",
            text("DATE(transaction_date_time)"),
            unique=True,
            postgresql_where=text("operation_type = 'auto_subtract' AND amount < 0"),
        ),
    )


class WBBonusPayment(BaseTable):
    """Модель для хранения информации о бонусах"""

    __tablename__ = "wbbonuspayment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet: Mapped["WBCabinet"] = relationship("WBCabinet", back_populates="bonus_payments")

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    # 'add', 'subtract', 'reset', 'auto_subtract'
    operation_type: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'subtract'"))
    admin_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_wb_bonus_payment_cabinet_id", "wb_cabinet_id"),
        Index("idx_wb_bonus_payment_date", "transaction_date_time"),
        Index("idx_wb_bonus_payment_admin", "admin_user_id"),
        Index("idx_wb_bonus_payment_operation", "operation_type"),
        Index(
            "idx_unique_daily_auto_bonus_charge",
            "wb_cabinet_id",
            text("DATE(transaction_date_time)"),
            unique=True,
            postgresql_where=text(
                "operation_type = 'auto_subtract' AND amount < 0 AND admin_user_id IS NULL"
            ),
        ),
    )


class WBCategory(BaseTable):
    cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet: Mapped['WBCabinet'] = relationship(
        "WBCabinet", back_populates="wb_categories"
    )
    wb_category_name: Mapped[str] = mapped_column(String, nullable=False)
    wb_cards: Mapped[list["WBCard"]] = relationship("WBCard", back_populates="wb_category", uselist=True)
    __table_args__ = (Index("ix_wb_category_name", "wb_category_name"),)


class WBToken(BaseTable):
    def __repr__(self) -> str:
        return f"user_id: {self.user_id}"

    api_key: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped[User] = relationship("User", back_populates="wb_tokens", lazy="joined")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    shop_id: Mapped[str | None] = mapped_column(String, nullable=True)
    __table_args__ = (
        UniqueConstraint("api_key", "user_id", name="_api_key_user_id_uc"),
        Index("idx_shop_id", "shop_id"),
    )

    @property
    def __payload(self) -> dict[str, object]:
        try:
            result = jwt.decode(self.api_key, options={"verify_signature": False})
            if not isinstance(result, dict):
                raise exceptions.NotValidTokenError
            return cast(dict[str, object], result)
        except Exception:
            raise exceptions.NotValidTokenError

    def check_valid(self) -> bool:
        try:
            assert self.api_key
            result = jwt.decode(self.api_key, options={"verify_signature": False})
            return bool(result)
        except (ValueError, DecodeError):
            return False

    def get_payload(self, key: str) -> str | int | None:
        payload = self.__payload
        value = payload.get(key)
        if isinstance(value, (str, int)) or value is None:
            return value
        return None

    @property
    def __expires(self) -> datetime.datetime:
        exp = self.__payload.get("exp")
        if isinstance(exp, (int, float, str)):
            return datetime.datetime.fromtimestamp(int(exp))
        raise exceptions.NotValidTokenError

    @property
    def expires(self) -> datetime.datetime:
        return self.__expires

    def get_shop_id_from_token(self) -> str:
        sid = self.get_payload("sid")
        if isinstance(sid, str):
            return sid
        raise exceptions.NotValidTokenError

    @property
    def read_only(self) -> bool:
        return "Токен только на чтение" in self.categories

    @property
    def categories(self) -> set[str]:
        categories_map = {
            1: "Контент",
            2: "Аналитика",
            3: "Цены и скидки",
            4: "Маркетплейс",
            5: "Статистика",
            6: "Продвижение",
            7: "Вопросы и отзывы",
            8: "Рекомендации",
            30: "Токен только на чтение",
        }
        s = self.get_payload("s")
        categories = set()
        if isinstance(s, int):
            for bit_position, category_name in categories_map.items():
                if s & (1 << bit_position):
                    categories.add(category_name)
        return categories



@dataclass
class WBItemPosition:
    nmid: int | None = None
    position: int | None = None
    timestamp: datetime.datetime | None = None
    adv_id: int | None = None
    keyword_text: str | None = None
    adv_type: int | None = None

    @property
    def type_native(self) -> str:
        if self.adv_type == 9:
            return "search"
        elif self.adv_type == 8:
            return "auto"
        else:
            return "unknown"

    def to_dict(self) -> dict[str, object]:
        timestamp = self.timestamp
        str_timestamp = timestamp.isoformat() if timestamp else None
        return {
            "real_position": self.position,
            "promo_position": self.position,
            "base_position": self.position,
            "position": self.position,
            "keyword_text": self.keyword_text,
            "adv_id": self.adv_id,
            "nmid": self.nmid,
            "timestamp": str_timestamp,
            "adv_type": self.adv_type,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "WBItemPosition":
        position = WBItemPosition()
        raw_position = data.get("position")
        if isinstance(raw_position, int):
            position.position = raw_position
        elif isinstance(raw_position, str) and raw_position.isdigit():
            position.position = int(raw_position)
        else:
            # fallback старый ключ
            base_raw = data.get("base_position")
            if isinstance(base_raw, int):
                position.position = base_raw
            elif isinstance(base_raw, str) and base_raw.isdigit():
                position.position = int(base_raw)
            else:
                position.position = None

        raw_adv_id = data.get("adv_id")
        if isinstance(raw_adv_id, int):
            position.adv_id = raw_adv_id
        elif isinstance(raw_adv_id, str) and raw_adv_id.isdigit():
            position.adv_id = int(raw_adv_id)
        else:
            position.adv_id = None

        raw_nmid = data.get("nmid")
        if isinstance(raw_nmid, int):
            position.nmid = raw_nmid
        elif isinstance(raw_nmid, str) and raw_nmid.isdigit():
            position.nmid = int(raw_nmid)
        else:
            position.nmid = None

        # timestamp
        raw_ts = data.get("timestamp")
        if isinstance(raw_ts, str):
            try:
                position.timestamp = datetime.datetime.fromisoformat(raw_ts)
            except Exception:
                position.timestamp = None
        else:
            position.timestamp = None

        raw_kw = data.get("keyword_text")
        position.keyword_text = raw_kw if isinstance(raw_kw, str) else None

        raw_adv_type = data.get("adv_type")
        if isinstance(raw_adv_type, int):
            position.adv_type = raw_adv_type
        elif isinstance(raw_adv_type, str) and raw_adv_type.isdigit():
            position.adv_type = int(raw_adv_type)
        else:
            position.adv_type = None

        return position
