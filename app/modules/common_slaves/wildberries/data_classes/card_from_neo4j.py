import logging
import os
import re

import yaml
from image_master.database.database import Image

from .abc_card import WBCard

logger = logging.getLogger(__name__)




class CardFromDB(WBCard):
    def __init__(self, data: dict):
        super().__init__()
        self.__TEMPLATES_FOLDER = 'wb/cards_manager_old/category_templates'

        data = data.items()
        dict_ = {}
        for row in data:
            key = row[0]
            value = row[1]
            dict_[key] = value
        self._data = dict_



    @property
    def offer_id(self):
        return self._data['offer_id']


    @property
    def wb_mediaFiles(self):
        return self._data['wb_mediaFiles']


    @property
    def keyword(self):
        return self.keywords[0]

    @keyword.setter
    def keyword(self, value: str):
        self._data['keyword'] = value


    @property
    def wb_category_name(self):
        return self._data['wb_category_name']

    @property
    def wb_barcode(self):
        return str(self._data['wb_barcode'])

    @property
    def prefix(self):
        return self._data['prefix']


    @property
    def brand(self):
        return self._brand

    @brand.setter
    def brand(self, value: str):
        self._brand = value


    @property
    def stock(self)-> int:
        return self._stock


    @stock.setter
    def stock(self, value:int):
        assert isinstance(value, int)
        self._stock = value


    @property
    def price(self):
        return 1100


    @property
    def names(self):
        return self._data['names']

    @property
    def keywords(self):
        if 'keywords' in self._data:
            keywords = [re.sub('картин[аы] по номерам', "", keyword).strip() for keyword in self._data['keywords']]
        else:
            keywords = None
        return keywords


    @keywords.setter
    def keywords(self, value):
        self._data['keywords'] = value


    @property
    def main_image_obj_from_db(self) -> Image:
        return self._main_image_obj_from_db

    @main_image_obj_from_db.setter
    def main_image_obj_from_db(self, value):
        assert isinstance(value, Image)
        self._main_image_obj_from_db = Image

    @staticmethod
    def __generate_variants(input_str):
        pattern = re.compile(r'\(.+?\)')
        matchs = pattern.findall(input_str)
        matchs.reverse()
        variants = [input_str]
        for match in matchs:
            input_str = input_str.replace(match, '')
            variants.append(input_str)
        return variants

    def __replace_value_by_self(self, value):
        value = str(value)
        pattern = re.compile(
            r'<(.+?)>')  # Шаблон для поиска <имя_свойства> с минимальным количеством символов внутри <>
        matchs = pattern.findall(value)

        for match in matchs:
            property_name = match.strip()
            if hasattr(self, property_name):
                replacement = str(getattr(self, property_name))
                value = value.replace(f'<{property_name}>', replacement)
            else:
                raise Exception(f'Метод {property_name} в {self.__class__} не реализован!')

        return value

    def __get_template_for_category(self):
        path = os.path.join(self.__TEMPLATES_FOLDER,
                            self.wb_category_name.capitalize() + '.yaml'
                            )
        with open(path, 'r', encoding='utf-8') as file:
            chars_dict = yaml.safe_load(file)

        return chars_dict

    @staticmethod
    def __special_replacer(value):
        value = value.replace('()', '')
        value = value.replace('(', '')
        value = value.replace(')', '')
        value = re.sub(r'\(\d+\)', '', value)
        value = value.replace(', ', ',')
        value = value.replace(' ,', ',')
        value = value.replace('  ', ' ')
        value = value.strip()
        return value

    @property
    def wb_json_characteristics(self):
        """Ключевой метод: геренарица json для карточки"""

        def get_number(text):
            if text.startswith('"') and text.endswith('"'):
                return text
            # Проверка, является ли входное значение числом
            if isinstance(text, int) or isinstance(text, float):
                return text
            # Проверка на наличие только цифр и, возможно, десятичной точки
            if re.match(r'^-?\d+(\.\d+)?$', text):
                # Преобразование к float или int
                return float(text) if '.' in text else int(text)

            # Возвращение исходного текста, если есть другие символы
            return text


        def prepare_value(value):
            if isinstance(value, str):
                if match := re.match(r'str\((\d+)\)', value):
                    return str(match.group(1))
            value = self.__replace_value_by_self(value)
            value = self._parse_list(value)
            if isinstance(value, str):
                values = self.__generate_variants(value)
                values = [self.__special_replacer(value) for value in values]
                value = self._get_best_value(char, values)
                value = get_number(value)
                return value

        temp_dict = self.__get_template_for_category()
        characteristics = []


        def get_characteristic(value):
            if isinstance(value, list):
                return [prepare_value(v) for v in value]
            else:
                return prepare_value(value)

        for char, value in temp_dict.items():
            try:
                value = get_characteristic(value)
            except (FileNotFoundError, KeyError) as exc:
                logger.debug(f'Ошибка: {self.offer_id}. Exc: {exc}')
                continue
            characteristics.append({char: value})
        return characteristics



    @staticmethod
    def _get_best_value(char, values):
        if char == 'Наименование':
            max_len = 60
        else:
            max_len = 5000
        values = [value for value in values if len(value) <= max_len]
        values.sort(key=lambda key: len(key), reverse=True)
        value = values[0]
        return value

    @property
    def simple_name(self):
        return self.keyword.capitalize()



    @property
    def colors(self):
        return self._data['colors']

    @colors.setter
    def colors(self, value: list):
        self._data['colors'] = value


    @property
    def color(self):
        return self.colors[0]



    @property
    def purpose_of_gift(self)-> list:
        return self._data['purpose_of_gift']


    @purpose_of_gift.setter
    def purpose_of_gift(self, value):
        self._data['purpose_of_gift'] = value

    @property
    def what_on_image (self):
        return self._data['what_on_image']


    @what_on_image.setter
    def what_on_image(self, value):
        self._data['what_on_image'] = value

    @property
    def describe(self):
        pattern = r'([.,])(?![ \n])'
        replacement = r'\1 '
        self._data['describe'] = re.sub(pattern, replacement, self._data['describe'])
        return self._data['describe']

    @describe.setter
    def describe(self, value):
        self._data['describe'] = value

    def _parse_list(self, value: str):
        pattern = r'^\[(.+)\]$'
        match = re.match(pattern, value)
        if match:
            # Получение строки внутри квадратных скобок
            inner_value = match.group(1)
            # Разбиение строки на элементы списка
            value_list = [v.strip().strip("'\"") for v in inner_value.split(',') if v.strip()]
            return value_list
        else:
            return value

    @property
    def simple_describe(self):
        return self._data['simple_describe']

    @simple_describe.setter
    def simple_describe(self, value):
        self._data['simple_describe'] = value

    def add_foto(self, photo_path):
        self.wb_local_fotos.append(photo_path)



