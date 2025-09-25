from pydantic import BaseModel
from typing import Any, cast


class Subject(BaseModel):
    id: int
    name: str


class Menu(BaseModel):
    id: int
    name: str


class UnitedParams(BaseModel):
    # catalogCPM: int
    searchCPM: int
    subject: Subject
    # menus: List[Menu]
    nms: list[int]


class AutoParams(BaseModel):
    active: dict[str, bool]  # Предполагается, что 'active' это словарь с булевыми значениями
    # Добавьте другие поля, которые ожидаются в `autoParams`


class AdvData(BaseModel):
    endTime: str
    createTime: str
    changeTime: str
    startTime: str
    name: str
    unitedParams: list[UnitedParams] | None = None
    dailyBudget: int
    advertId: int
    status: int
    type: int
    autoParams: AutoParams | None = None


class Balances:
    def __init__(self, data: dict[str, Any]):
        self.balance = data.get("balance", 0)  # Счет
        self.net = data.get("net", 0)  # Баланс
        self.bonus = data.get("bonus", 0)  # Бонусы


class AdvType:
    NMID_TEST = "NMID_TEST"
    KEYWORD_TEST = "KEYWORD_TEST"


class Statistic:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        assert isinstance(data, list)
        self._data: dict[str, Any] = data[0]

    @property
    def advert_id(self) -> int:
        return cast(int, self._data["advertId"])

    @property
    def begin(self) -> str:
        return cast(str, self._data["begin"])

    @property
    def end(self) -> str:
        return cast(str, self._data["end"])

    @property
    def days(self) -> list[Any]:
        return cast(list[Any], self._data["days"])

    @property
    def views(self) -> int:
        return cast(int, self._data["views"])

    @property
    def clicks(self) -> int:
        return cast(int, self._data["clicks"])

    @property
    def ctr(self) -> float:
        return cast(float, self._data["ctr"])

    @property
    def cpc(self) -> float:
        return cast(float, self._data["cpc"])

    @property
    def sum(self) -> float:
        return cast(float, self._data["sum"])

    @property
    def atbs(self) -> int:
        return cast(int, self._data["atbs"])

    @property
    def orders(self) -> int:
        return cast(int, self._data["orders"])

    @property
    def cr(self) -> float:
        return cast(float, self._data["cr"])

    @property
    def in_shks(self) -> int:
        return cast(int, self._data["shks"])

    @property
    def sum_price(self) -> float:
        return cast(float, self._data["sum_price"])
