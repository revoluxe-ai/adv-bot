"""
Базовый класс для типизации WB-миксинов.

"""

from abc import ABC, abstractmethod
from typing import Any


class WBApiMixin(ABC):
    def __init__(self) -> None:
        self.api_call_state: dict[str, dict[str, Any]] = {}

    @property
    @abstractmethod
    def shop_id(self) -> str:
       pass

    @abstractmethod
    async  def set_next_token(self) -> None:
        pass
