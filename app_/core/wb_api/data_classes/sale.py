class Sale:
    def __init__(self, data):
        self._data = data

    @property
    def barcode(self):
        return self._data["barcode"]

    @property
    def category_name(self):
        return self._data["subject"]

    @property
    def brand(self):
        return self._data["brand"]

    @property
    def spp(self):
        return self._data["spp"]

    @property
    def price(self):
        return self._data["finishedPrice"]

    @property
    def sales(self):
        return self._data["sales"]

    @property
    def nmid(self):
        return self._data["nmId"]
