from abc import ABC, abstractmethod
from typing import Any


class ShopInterface(ABC):
    @property
    @abstractmethod
    def media_template(self) -> Any:
        pass
