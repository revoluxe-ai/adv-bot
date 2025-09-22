import datetime
from typing import Optional


class WBTokenMock:
    def __init__(self, api_key: str, shop_id: int = 123456):
        self.api_key = api_key
        self.user_id = 12345
        self.active = True
        self.shop_id = shop_id

        # Создаем mock payload с датой истечения через месяц
        self._mock_payload = {
            "sid": shop_id,
            "s": 1275,  # бинарная маска для категорий (1,2,8,10 биты = Контент, Аналитика, Рекомендации, Статистика)
            "exp": int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp()),
            "uid": 987654321,
        }

    def __repr__(self) -> str:
        return f"user_id: {self.user_id}"

    @property
    def _WBTokenMock__payload(self) -> dict[str, int]:
        """Приватное свойство для payload"""
        return self._mock_payload

    def check_valid(self) -> bool:
        """Всегда возвращает True для мока"""
        return True

    def get_payload(self, key: str) -> str | int | None:
        """Возвращает значение из мокового payload"""
        return self._mock_payload.get(key)

    @property
    def __expires(self) -> datetime.datetime:
        """Приватное свойство для даты истечения"""
        exp_timestamp = self._mock_payload.get("exp")
        if exp_timestamp is None:
            raise ValueError("No expiration timestamp in payload")
        return datetime.datetime.fromtimestamp(exp_timestamp)

    @property
    def expires(self) -> datetime.datetime:
        """Публичное свойство для даты истечения"""
        return self.__expires

    def get_shop_id_from_token(self) -> Optional[str]:
        """Возвращает shop_id из токена"""
        sid = self.get_payload("sid")
        return str(sid) if sid is not None else None

    @property
    def read_only(self) -> bool:
        """Проверяет, является ли токен read-only"""
        return "Токен только на чтение" in self.categories

    @property
    def categories(self) -> set[str]:
        """Возвращает набор категорий на основе битовой маски"""
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
        if not isinstance(s, int):
            return set()
        categories = set()
        for bit_position, category_name in categories_map.items():
            if s & (1 << bit_position):
                categories.add(category_name)
        return categories
