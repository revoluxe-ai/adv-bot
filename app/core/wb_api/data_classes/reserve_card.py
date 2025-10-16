from typing import Any

class ReserveCard:
    _wb_barcode: Any
    _offer_id: Any
    _unique_name: Any

    @property
    def wb_barcode(self) -> Any:
        return self._wb_barcode

    @wb_barcode.setter
    def wb_barcode(self, value: Any):
        self._wb_barcode = value

    @property
    def offer_id(self) -> Any:
        return self._offer_id

    @offer_id.setter
    def offer_id(self, value: Any):
        self._offer_id = value

    @property
    def unique_name(self) -> Any:
        return self._unique_name

    @unique_name.setter
    def unique_name(self, value: Any):
        self._unique_name = value
