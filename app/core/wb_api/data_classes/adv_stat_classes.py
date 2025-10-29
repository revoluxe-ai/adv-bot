from typing import Any


class SimpleStat:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def clicks(self) -> int:
        return int(self._data["clicks"])

    @property
    def cpc(self) -> float:
        return float(self._data["cpc"])

    @property
    def ctr(self) -> float:
        return float(self._data["ctr"])

    @property
    def views(self) -> int:
        return int(self._data["views"])

    @property
    def spend(self) -> float:
        return float(self._data["spend"])
