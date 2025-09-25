from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, cast


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
    autoParams: Any | None = None

    @property
    @abstractmethod
    def cpm(self) -> int:
        pass

    @property
    @abstractmethod
    def nmids(self) -> list[int]:
        pass

    @property
    def category_name(self) -> str:
        if self.autoParams:
            return cast(str, self.autoParams.subject.name)
        return ""

    @property
    def subject_id(self) -> int:
        if self.autoParams:
            return cast(int, self.autoParams.subject.id)
        return 0

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
