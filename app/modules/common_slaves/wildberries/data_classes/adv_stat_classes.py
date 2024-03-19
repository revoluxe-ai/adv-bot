
class SimpleStat:
    def __init__(self, data):
        self._data = data

    @property
    def clicks(self):
        return self._data['clicks']

    @property
    def  cpc(self):
        return self._data['cpc']

    @property
    def ctr(self):
        return self._data['ctr']

    @property
    def views(self):
        return self._data['views']

    @property
    def spend(self):
        return self._data['spend']




