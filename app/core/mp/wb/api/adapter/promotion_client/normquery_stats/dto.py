from datetime import date

from pydantic import BaseModel, PrivateAttr


class NormqueryStat(BaseModel):
    norm_query: str
    views: int
    clicks: int
    ctr: float
    cpm: float | None
    add_to_cart: int | None
    orders: int
    cpc: float | None
    avr_pos: float | None


class NormqueryStatsDTO(BaseModel):
    adv_id: int
    nmid: int
    stats: list[NormqueryStat]
    _day: date | None = PrivateAttr(default=None)

    @property
    def day(self) -> date:
        if self._day is None:
            raise AttributeError("day не установлен")
        return self._day
    
    @day.setter
    def day(self, value: date) -> None:
        self._day = value



