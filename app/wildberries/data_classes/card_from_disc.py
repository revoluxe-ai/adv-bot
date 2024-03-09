from .abc_card import WBCard, Path
import re
import yaml
import os
from image_master.database.model import Image
from image_master.database.model import WB_CARD_MEDIA_FOLDER

class CardFromDisc(WBCard):

    def __init__(self, wb_category_name: str, name: str, uuid_:str, keywords: list, size: str, fotos: list,
                 stock):
        """
        :param path:
        """
        self._stock = stock
        self._uuid = uuid_
        self._size = size
        self._name = name
        self._keywords = keywords
        self._wb_category_name = wb_category_name

        current_module_path = os.path.abspath(__file__)
        # Получение пути к директории, содержащей текущий модуль
        current_module_directory = os.path.dirname(current_module_path)
        # Соединение пути с базовой директорией
        self.__BASE_FOLDER = os.path.join(current_module_directory, '../cards_manager_old/category_templates')
        super().__init__()

    @property
    def stock(self) -> int:
        return self._stock


    @property
    def main_image_obj_from_db(self):
        return self._main_image_obj_db


    @main_image_obj_from_db.setter
    def main_image_obj_from_db(self, value):
        assert isinstance(value, Image)
        self._main_image_obj_db = value


    @property
    def wb_tags(self):
        return None



    @property
    def wb_barcode(self):
        return self._wb_barcode


    @wb_barcode.setter
    def wb_barcode(self, value):
        self._wb_barcode = value

    @property
    def wb_local_fotos(self):
        brand_folder = os.path.join(WB_CARD_MEDIA_FOLDER, self.brand)
        card_folder = os.path.join(brand_folder, self.offer_id)
        media = []
        for file in os.listdir(card_folder):
            file_path = os.path.join(card_folder, file)





    @property
    def wb_category_name(self):
        return self._wb_category_name

    @property
    def size(self):
        return self._size

    @property
    def keyword(self):
        return self._keywords[0]

    @property
    def name(self):
        return self._name


    @property
    def unique_name(self):
        return self._uuid

    @property
    def offer_id(self):
        return self._offer_id

    @offer_id.setter
    def offer_id(self, value):
        self._offer_id = value





    @wb_category_name.setter
    def wb_category_name(self, value):
        self._wb_category_name = value


    @property
    def price(self):
        if self.wb_category_name == 'Картины':
            if self.size in ('40x50', '40X50'):
                price = 1000
            else:
                price = 1300
        else:
            raise Exception('Категория не описана в ценах')
        return price




    @property
    def wb_status(self):
        return self._wb_status

    @wb_status.setter
    def wb_status(self, value):
        self._wb_status = value

    @property
    def prefix(self):
        if self.wb_category_name == 'Картины':
            size = re.match('(\d{2,3}).(\d{2,3})', self.size)
            size = size.group(1) + size.group(2)
            prefix = f'MSC{size}Z'
        else:
            raise Exception()
        return  prefix


    @wb_barcode.setter
    def wb_barcode(self, value):
        if isinstance(value, str):
            self._wb_barcode = value


    @property
    def chrtID(self):
        return self._chrtID


    @chrtID.setter
    def chrtID(self, value):
        self._chrtID = value


    @property
    def nmid(self):
        return self._nmid


    @property
    def imtID(self):
        return self._itmID



    @property
    def names(self):
        return [self._name]


    @nmid.setter
    def nmid(self, value):
        self._nmid = value


    @property
    def keywords(self):
        return [keyword for keyword in self._keywords if keyword]


