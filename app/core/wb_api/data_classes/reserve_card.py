class ReserveCard:
    @property
    def wb_barcode(self):
        return self._wb_barcode

    @wb_barcode.setter
    def wb_barcode(self, value):
        self._wb_barcode = value

    @property
    def offer_id(self):
        return self._offer_id

    @offer_id.setter
    def offer_id(self, value):
        self._offer_id = value

    @property
    def unique_name(self):
        return self._unique_name

    @unique_name.setter
    def unique_name(self, value):
        self._unique_name = value
