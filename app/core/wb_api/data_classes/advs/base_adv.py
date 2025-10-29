from abc import ABC, abstractmethod
from datetime import datetime
import typing

from pydantic import BaseModel, ConfigDict


class Adv(BaseModel, ABC):
    model_config = ConfigDict(from_attributes=True)  # Позволяет использовать obj.__dict__

    advertId: int
    name: str
    status: int
    type: int
    changeTime: datetime  # Меняем int → datetime
    createTime: datetime
    dailyBudget: float
    endTime: datetime
    startTime: datetime

    @property
    @abstractmethod
    def cpm(self: typing.Any) -> int:
        pass

    @property
    @abstractmethod
    def nmids(self: typing.Any) -> list[int]:
        pass

    @property
    @abstractmethod
    def category_name(self: typing.Any) -> str:
        pass

    @property
    @abstractmethod
    def subject_id(self: typing.Any) -> int:
        pass

    @property
    def status_native(self) -> str:
        return {
            4: "ready_for_start",
            11: "pause",
            9: "started",
            7: "done",
        }.get(self.status, f"Статус {self.status} не реализован")

    @property
    def status_native_ru(self) -> str:
        return {
            4: "Готов к запуску",
            11: "Пауза",
            9: "Запущен",
            7: "Завершен",
        }.get(self.status, f"Статус {self.status} не реализован")
