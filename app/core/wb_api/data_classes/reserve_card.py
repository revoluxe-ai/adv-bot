from typing import Any

class ReserveCard:
    _wb_barcode: str
    _offer_id: str
    _unique_name: str

    @property
    def wb_barcode(self) -> str:
        return self._wb_barcode

    @wb_barcode.setter
    def wb_barcode(self, value: str):
        self._wb_barcode = value

    @property
    def offer_id(self) -> str:
        return self._offer_id

    @offer_id.setter
    def offer_id(self, value: str):
        self._offer_id = value

    @property
    def unique_name(self) -> str:
        return self._unique_name

    @unique_name.setter
    def unique_name(self, value: str):
        self._unique_name = value
