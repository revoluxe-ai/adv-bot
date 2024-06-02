from .abc_card import WBCard


class CardFromWB(WBCard):

    @property
    def data(self):
        return self._data

    @property
    def shop_name(self):
        return self._shop_name

    @shop_name.setter
    def shop_name(self, value):
        self._shop_name = value



    def __str__(self):
        name = []
        name.append('<'*5 + '>'*5)
        name.append(str(self.nmid))
        name.append('<'*5 + '>'*5)
        return '\n'.join(name)

    def __init__(self, data):
        super().__init__()
        self._data = data

    @property
    def name(self):
        return self._data['title']


    @property
    def techSize(self):
        return self._data['sizes'][0]['techSize']

    @property
    def wb_mediaFiles(self):
        media =  [image['big'] for image in self._data.get('photos', [])]
        return media

    @property
    def subjectID(self):
        return self._data['subjectID']

    @property
    def wb_barcode(self):
        return self._data['sizes'][0]['skus'][0]


    @property
    def offer_id(self):
        return self._data['vendorCode']

    @property
    def brand(self):
        return self._data['brand']

    @property
    def characterisics(self):
        return self._data['characteristics']


    def createdAt(self):
        return self._data['createdAt']


    def updatedAt(self):
        return self._data['updatedAt']


    @property
    def wb_category_name(self):
        return self._data['subjectName']

    @property
    def nmid(self)-> int:
        return int(self._data['nmID'])


    @property
    def imtID(self):
        return self._data['imtID']




class CardFromError:
    def __init__(self, dict_):
        self._nmid = dict_['nmid']
        self._offer_id = dict_['offer_id']

    @property
    def nmid(self):
        return self._nmid

    @property
    def offer_id(self):
        return self._offer_id




