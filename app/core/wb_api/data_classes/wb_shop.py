from python_modules import path_setting_funcs

from . import interfaces


class WbShop(interfaces.ShopInterface):
    def __init__(self, setting_path: str, name_shop: str):
        self._setting_path = setting_path
        self._name_shop = name_shop

    def _load_settings(self):
        shops_dict = path_setting_funcs.get_document_by_key_name(
            self._setting_path, "shops"
        )
        for shop in shops_dict:
            if shop["name"] == self._name_shop:
                return shop

    @property
    def media_template(self):
        return self._load_settings().get("media_template")

    @property
    def api_key(self):
        return self._load_settings().get("wb-api-standart")

    @property
    def standart_api(self):
        return self._load_settings().get("wb-api-standart")

    @property
    def brand(self):
        return self._load_settings().get("brand")

    @property
    def name(self):
        return self._load_settings().get("name")

    @property
    def store_id(self):
        return self._load_settings().get("store_id")

    @property
    def max_cards(self):
        max_cards = self._load_settings().get("max_cards")
        return int(max_cards) if max_cards else None

    @property
    def categories(self):
        categories = self._load_settings().get("categories")
        assert isinstance(categories, list), "Categories should be a list"
        return categories

    @property
    def cpm(self):
        return int(self._load_settings().get("cpm"))

    @property
    def min_ctr(self):
        return round(
            float(self._load_settings().get("min_ctr", 100)), 2
        )  # Указан 0 в качестве значения по умолчанию

    @property
    def kn_for_ml(self):
        return int(
            self._load_settings().get("kn_for_ml", 1)
        )  # Указан 0 в качестве значения по умолчанию

    def __repr__(self):
        return self.name

