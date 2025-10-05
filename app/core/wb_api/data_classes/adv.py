import re

from pydantic import BaseModel


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
    active: dict[
        str, bool
    ]  # Предполагается, что 'active' это словарь с булевыми значениями
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
    def __init__(self, data: dict):
        self.balance = data.get("balance", 0)  # Счет
        self.net = data.get("net", 0)  # Баланс
        self.bonus = data.get("bonus", 0)  # Бонусы


class AdvType:
    NMID_TEST = "NMID_TEST"
    KEYWORD_TEST = "KEYWORD_TEST"


class Adv:
    def __repr__(self):
        return f"Name: {self.name}, Advert ID: {self.advertId},  Status: {self.status_native_ru}, Type: {self.adv_type}"

    def __init__(self, data):
        self._data = data

    @property
    def category_name(self):
        return self._data["autoParams"]["subject"]["name"]

    @property
    def subject_id(self):
        return self._data["autoParams"]["subject"]["id"]

    @property
    def adv_type(self) -> int:
        return self._data["type"]

    @adv_type.setter
    def adv_type(self, value: int):
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
    def advertId(self):
        return self._data["advertId"]

    @property
    def changeTime(self):
        return self._data["changeTime"]

    @property
    def createTime(self):
        return self._data["createTime"]

    @property
    def dailyBudget(self):
        return self._data["dailyBudget"]

    @property
    def endTime(self):
        return self._data["endTime"]

    @property
    def name(self):
        return self._data["name"]

    @property
    def startTime(self):
        return self._data["startTime"]

    @property
    def status(self):
        return self._data["status"]

    @property
    def type(self):
        return self._data["type"]

    @property
    def cpm(self):
        return self._data["price"]

    @property
    def data(self):
        return self._data

    @property
    def active(self):
        class Active:
            def __init__(self, active_data):
                self._active_data = active_data

            @property
            def booster(self):
                return self._active_data["booster"]

            @property
            def carousel(self):
                return self._active_data["carousel"]

            @property
            def recom(self):
                return self._active_data["recom"]

        active = Active(self._data["autoParams"]["active"])
        return active

    @property
    def nmids(self):
        try:
            if self._data["type"] == 9:
                return self._data["unitedParams"][0]["nms"]
            else:
                nmids = self._data["autoParams"]["nms"]
                if nmids:
                    return nmids
                else:
                    raise Exception("NMID не найден")
        except:
            nmids = re.findall(r"(?<!\[)\d{7,9}(?!\])", self.name)
            nmids = [int(nmid) for nmid in nmids]
            return nmids if nmids else []


class Statistic:
    def __init__(self, data):
        assert isinstance(data, list)
        self._data = data[0]

    @property
    def advert_id(self):
        return self._data["advertId"]

    @property
    def begin(self):
        return self._data["begin"]

    @property
    def end(self):
        return self._data["end"]

    @property
    def days(self):
        return self._data["days"]

    @property
    def views(self):
        return self._data["views"]

    @property
    def clicks(self):
        return self._data["clicks"]

    @property
    def ctr(self):
        return self._data["ctr"]

    @property
    def cpc(self):
        return self._data["cpc"]

    @property
    def sum(self):
        return self._data["sum"]

    @property
    def atbs(self):
        return self._data["atbs"]

    @property
    def orders(self):
        return self._data["orders"]

    @property
    def cr(self):
        return self._data["cr"]

    @property
    def in_shks(self):
        return self._data["shks"]

    @property
    def sum_price(self):
        return self._data["sum_price"]
