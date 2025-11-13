from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v0_config_response_200_config_item import GetAdvV0ConfigResponse200ConfigItem
    from ..models.v0_get_config_categories_response import V0GetConfigCategoriesResponse


T = TypeVar("T", bound="GetAdvV0ConfigResponse200")


@_attrs_define
class GetAdvV0ConfigResponse200:
    """
    Attributes:
        categories (Union[Unset, List['V0GetConfigCategoriesResponse']]): Spisok kategorij tovarov (predmetov) s
            minimal'no dopustimymi stavkami
        config (Union[Unset, List['GetAdvV0ConfigResponse200ConfigItem']]): Spisok osnovnyh parametrov konfiguratsii s
            dopustimymi znachenijami
    """

    categories: Union[Unset, List["V0GetConfigCategoriesResponse"]] = UNSET
    config: Union[Unset, List["GetAdvV0ConfigResponse200ConfigItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        categories: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.categories, Unset):
            categories = []
            for categories_item_data in self.categories:
                categories_item = categories_item_data.to_dict()
                categories.append(categories_item)

        config: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.config, Unset):
            config = []
            for config_item_data in self.config:
                config_item = config_item_data.to_dict()
                config.append(config_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if categories is not UNSET:
            field_dict["categories"] = categories
        if config is not UNSET:
            field_dict["config"] = config

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_adv_v0_config_response_200_config_item import GetAdvV0ConfigResponse200ConfigItem
        from ..models.v0_get_config_categories_response import V0GetConfigCategoriesResponse

        d = src_dict.copy()
        categories = []
        _categories = d.pop("categories", UNSET)
        for categories_item_data in _categories or []:
            categories_item = V0GetConfigCategoriesResponse.from_dict(categories_item_data)

            categories.append(categories_item)

        config = []
        _config = d.pop("config", UNSET)
        for config_item_data in _config or []:
            config_item = GetAdvV0ConfigResponse200ConfigItem.from_dict(config_item_data)

            config.append(config_item)

        get_adv_v0_config_response_200 = cls(
            categories=categories,
            config=config,
        )

        get_adv_v0_config_response_200.additional_properties = d
        return get_adv_v0_config_response_200

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
