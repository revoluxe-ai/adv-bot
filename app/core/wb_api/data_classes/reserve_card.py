from typing import Any


class ReserveCard:
    def __init__(self) -> None:
        self._wb_barcode: Any = None
        self._offer_id: Any = None
        self._unique_name: Any = None

    @property
    def wb_barcode(self) -> Any:
        return self._wb_barcode

    @wb_barcode.setter
    def wb_barcode(self, value: Any) -> None:
        self._wb_barcode = value

    @property
    def offer_id(self) -> Any:
        return self._offer_id

    @offer_id.setter
    def offer_id(self, value: Any) -> None:
        self._offer_id = value

    @property
    def unique_name(self) -> Any:
        return self._unique_name

    @unique_name.setter
    def unique_name(self, value: Any) -> None:
        self._unique_name = value
