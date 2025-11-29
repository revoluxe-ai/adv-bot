from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v0_config_response_200_config_item import (
        GetAdvV0ConfigResponse200ConfigItem,
    )
    from ..models.v0_get_config_categories_response import V0GetConfigCategoriesResponse


T = TypeVar("T", bound="GetAdvV0ConfigResponse200")


@_attrs_define
class GetAdvV0ConfigResponse200:
    """
    Attributes:
        categories (list[V0GetConfigCategoriesResponse] | Unset): List of product categories (subjects) with minimum
            allowable rates
        config (list[GetAdvV0ConfigResponse200ConfigItem] | Unset): List of the main configuration parameters with
            acceptable values
    """

    categories: list[V0GetConfigCategoriesResponse] | Unset = UNSET
    config: list[GetAdvV0ConfigResponse200ConfigItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.get_adv_v0_config_response_200_config_item import (
            GetAdvV0ConfigResponse200ConfigItem,
        )
        from ..models.v0_get_config_categories_response import (
            V0GetConfigCategoriesResponse,
        )

        categories: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.categories, Unset):
            categories = []
            for categories_item_data in self.categories:
                categories_item = categories_item_data.to_dict()
                categories.append(categories_item)

        config: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.config, Unset):
            config = []
            for config_item_data in self.config:
                config_item = config_item_data.to_dict()
                config.append(config_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if categories is not UNSET:
            field_dict["categories"] = categories
        if config is not UNSET:
            field_dict["config"] = config

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v0_config_response_200_config_item import (
            GetAdvV0ConfigResponse200ConfigItem,
        )
        from ..models.v0_get_config_categories_response import (
            V0GetConfigCategoriesResponse,
        )

        d = dict(src_dict)
        _categories = d.pop("categories", UNSET)
        categories: list[V0GetConfigCategoriesResponse] | Unset = UNSET
        if _categories is not UNSET:
            categories = []
            for categories_item_data in _categories:
                categories_item = V0GetConfigCategoriesResponse.from_dict(
                    categories_item_data
                )

                categories.append(categories_item)

        _config = d.pop("config", UNSET)
        config: list[GetAdvV0ConfigResponse200ConfigItem] | Unset = UNSET
        if _config is not UNSET:
            config = []
            for config_item_data in _config:
                config_item = GetAdvV0ConfigResponse200ConfigItem.from_dict(
                    config_item_data
                )

                config.append(config_item)

        get_adv_v0_config_response_200 = cls(
            categories=categories,
            config=config,
        )

        get_adv_v0_config_response_200.additional_properties = d
        return get_adv_v0_config_response_200

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
