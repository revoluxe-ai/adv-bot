from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from .base_table import BaseTable
import datetime
from typing import cast

class WBToken(BaseTable):
    api_key = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="wb_tokens", lazy="joined")
    active = Column(Boolean, default=True)
    shop_id = Column(String, nullable=True)
    __table_args__ = (
        UniqueConstraint("api_key", "user_id", name="_api_key_user_id_uc"),
        Index("idx_shop_id", "shop_id"),
    )

    def __repr__(self):
        return f"user_id: {self.user_id}"

    @property
    def hash(self):
        return hash(self.api_key)

    @property
    def __payload(self):
        # Lazy import jwt to avoid hard dependency at import time
        try:
            import jwt
        except Exception:
            raise RuntimeError("PyJWT is required to decode token payloads (install 'PyJWT')")
        # from .excs import NotValidTokenError  # Импортируйте при необходимости
        try:
            result = jwt.decode(cast(str, self.api_key), options={"verify_signature": False})
            return result
        except Exception:
            # raise NotValidTokenError  # Раскомментируйте при наличии
            raise

    def check_valid(self) -> bool:
        try:
            assert self.api_key
            try:
                import jwt
            except Exception:
                return False
            result = jwt.decode(cast(str, self.api_key), options={"verify_signature": False})
            return bool(result)
        except Exception:
            return False

    def get_payload(self, key):
        payload = self.__payload
        return payload.get(key)

    @property
    def __expires(self):
        # Use timezone-aware datetime in UTC
        exp = self.__payload.get("exp")
        return datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc)

    @property
    def expires(self):
        return self.__expires

    def get_shop_id_from_token(self) -> str:
        return self.get_payload("sid")

    @property
    def read_only(self) -> bool:
        return "Токен только на чтение" in self.categories

    @property
    def categories(self):
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
        if s is not None:
            for bit_position, category_name in categories_map.items():
                if s & (1 << bit_position):
                    categories.add(category_name)
        return categories

    @property
    def is_expired(self) -> bool:
        try:
            return datetime.datetime.now(datetime.timezone.utc) >= self.__expires
        except Exception:
            return True
