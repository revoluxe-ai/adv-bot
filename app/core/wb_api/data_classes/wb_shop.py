from typing import Any, Optional

from python_modules import path_setting_funcs

from . import interfaces


class WbShop(interfaces.ShopInterface):
    def __init__(self, setting_path: str, name_shop: str):
        self._setting_path = setting_path
        self._name_shop = name_shop

    def _load_settings(self) -> dict[str, Any]:
        shops_dict = path_setting_funcs.get_document_by_key_name(
            self._setting_path, "shops"
        )
        for shop in shops_dict:
            if shop["name"] == self._name_shop:
                return shop
        raise ValueError(f"Shop with name '{self._name_shop}' not found")

    @property
    def media_template(self) -> Any:
        return self._load_settings().get("media_template")

    @property
    def api_key(self) -> Any:
        return self._load_settings().get("wb-api-standart")

    @property
    def standart_api(self) -> Any:
        return self._load_settings().get("wb-api-standart")

    @property
    def brand(self) -> Any:
        return self._load_settings().get("brand")

    @property
    def name(self) -> Any:
        return self._load_settings().get("name")

    @property
    def store_id(self) -> Any:
        return self._load_settings().get("store_id")

    @property
    def max_cards(self) -> Optional[int]:
        max_cards = self._load_settings().get("max_cards")
        return int(max_cards) if max_cards else None

    @property
    def categories(self) -> list[Any]:
        categories = self._load_settings().get("categories")
        assert isinstance(categories, list), "Categories should be a list"
        return categories

    @property
    def cpm(self) -> int:
        value = self._load_settings().get("cpm")
        if value is None:
            raise ValueError("CPM value is required but not found")
        return int(value)

    @property
    def min_ctr(self) -> float:
        return round(
            float(self._load_settings().get("min_ctr", 100)), 2
        )  # Указан 0 в качестве значения по умолчанию

    @property
    def kn_for_ml(self) -> int:
        return int(
            self._load_settings().get("kn_for_ml", 1)
        )  # Указан 0 в качестве значения по умолчанию

    def __repr__(self) -> str:
        return self.name
