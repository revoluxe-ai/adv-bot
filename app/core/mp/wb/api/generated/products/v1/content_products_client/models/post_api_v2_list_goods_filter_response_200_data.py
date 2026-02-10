from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.goods_list import GoodsList


T = TypeVar("T", bound="PostApiV2ListGoodsFilterResponse200Data")


@_attrs_define
class PostApiV2ListGoodsFilterResponse200Data:
    """Dannye otveta

    Attributes:
        list_goods (list[GoodsList]): Informatsija o tovarah
    """

    list_goods: list[GoodsList]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        list_goods = []
        for list_goods_item_data in self.list_goods:
            list_goods_item = list_goods_item_data.to_dict()
            list_goods.append(list_goods_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "listGoods": list_goods,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.goods_list import GoodsList

        d = dict(src_dict)
        list_goods = []
        _list_goods = d.pop("listGoods")
        for list_goods_item_data in _list_goods:
            list_goods_item = GoodsList.from_dict(list_goods_item_data)

            list_goods.append(list_goods_item)

        post_api_v2_list_goods_filter_response_200_data = cls(
            list_goods=list_goods,
        )

        post_api_v2_list_goods_filter_response_200_data.additional_properties = d
        return post_api_v2_list_goods_filter_response_200_data

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
