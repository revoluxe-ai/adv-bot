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
