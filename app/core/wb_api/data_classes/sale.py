from typing import Any


class Sale:
    def __init__(self, data: dict[str, Any]):
        self._data = data

    @property
    def barcode(self) -> Any:
        return self._data["barcode"]

    @property
    def category_name(self) -> Any:
        return self._data["subject"]

    @property
    def brand(self) -> Any:
        return self._data["brand"]

    @property
    def spp(self) -> Any:
        return self._data["spp"]

    @property
    def price(self) -> Any:
        return self._data["finishedPrice"]

    @property
    def sales(self) -> Any:
        return self._data["sales"]

    @property
    def nmid(self) -> Any:
        return self._data["nmId"]
