import re

from pydantic import BaseModel, Field
from typing import Any, Callable, cast


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
    active: dict[str, bool] = Field(default_factory=dict) # Предполагается, что 'active' это словарь с булевыми значениями
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


class _Active:
    def __init__(self, active_data: dict[str, bool]) -> None:
        self._active_data = active_data

    @property
    def booster(self) -> bool:
        return self._active_data["booster"]

    @property
    def carousel(self) -> bool:
        return self._active_data["carousel"]

    @property
    def recom(self) -> bool:
        return self._active_data["recom"]


class Adv:
    def __repr__(self) -> str:
        return f"Name: {self.name}, Advert ID: {self.advertId},  Status: {self.status_native_ru}, Type: {self.adv_type}"

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def category_name(self) -> str:
        return cast(str, self._data["autoParams"]["subject"]["name"])

    @property
    def subject_id(self) -> int:
        return cast(int, self._data["autoParams"]["subject"]["id"])

    @property
    def adv_type(self) -> int:
        return cast(int, self._data["type"])

    @adv_type.setter
    def adv_type(self, value: int) -> None:
        self._type = value

    @property
    def status_native(self) -> str:
        if self.status == 4:
            return "ready_for_start"
        elif self.status == 11:
            return "pause"
        elif self.status == 9:
            return "started"
        elif self.status == 7:
            return "done"
        else:
            raise Exception(f"Статус {str(self.status)} не реализован")

    @property
    def status_native_ru(self) -> str:
        if self.status_native == "ready_for_start":
            return "готова к старту"
        elif self.status_native == "pause":
            return "пауза"
        elif self.status_native == "started":
            return "запущена"
        elif self.status_native == "done":
            return "завершена"
        else:
            raise Exception(f"Статус {str(self.status_native)} не реализован")

    @property
    def advertId(self) -> int:
        return cast(int, self._data["advertId"])

    @property
    def changeTime(self) -> str:
        return cast(str, self._data["changeTime"])

    @property
    def createTime(self) -> str:
        return cast(str, self._data["createTime"])

    @property
    def dailyBudget(self) -> int:
        return cast(int, self._data["dailyBudget"])

    @property
    def endTime(self) -> str:
        return cast(str, self._data["endTime"])

    @property
    def name(self) -> str:
        return cast(str, self._data["name"])

    @property
    def startTime(self) -> str:
        return cast(str, self._data["startTime"])

    @property
    def status(self) -> int:
        return cast(int, self._data["status"])

    @property
    def type(self) -> int:
        return cast(int, self._data["type"])

    @property
    def cpm(self) -> int:
        return cast(int, self._data["price"])

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @property
    def active(self) -> _Active:
        return _Active(cast(dict[str, bool], self._data["autoParams"]["active"]))

    @property
    def nmids(self) -> list[int]:
        try:
            if self._data["type"] == 9:
                return cast(list[int], self._data["unitedParams"][0]["nms"])
            else:
                nmids: list[int] | None = cast(list[int] | None, self._data["autoParams"]["nms"])
                if nmids:
                    return nmids
                else:
                    raise Exception("NMID не найден")
        except:
            nmids = re.findall(r"(?<!\[)\d{7,9}(?!\])", self.name)
            nmids = [int(nmid) for nmid in nmids]
            return nmids if nmids else []


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
