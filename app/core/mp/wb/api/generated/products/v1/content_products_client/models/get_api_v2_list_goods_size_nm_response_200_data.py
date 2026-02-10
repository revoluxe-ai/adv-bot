from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.size_good import SizeGood


T = TypeVar("T", bound="GetApiV2ListGoodsSizeNmResponse200Data")


@_attrs_define
class GetApiV2ListGoodsSizeNmResponse200Data:
    """Dannye otveta

    Attributes:
        list_goods (list[SizeGood] | None | Unset): Razmery tovara
    """

    list_goods: list[SizeGood] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        list_goods: list[dict[str, Any]] | None | Unset
        if isinstance(self.list_goods, Unset):
            list_goods = UNSET
        elif isinstance(self.list_goods, list):
            list_goods = []
            for list_goods_type_0_item_data in self.list_goods:
                list_goods_type_0_item = list_goods_type_0_item_data.to_dict()
                list_goods.append(list_goods_type_0_item)

        else:
            list_goods = self.list_goods

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if list_goods is not UNSET:
            field_dict["listGoods"] = list_goods

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.size_good import SizeGood

        d = dict(src_dict)

        def _parse_list_goods(data: object) -> list[SizeGood] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                list_goods_type_0 = []
                _list_goods_type_0 = data
                for list_goods_type_0_item_data in _list_goods_type_0:
                    list_goods_type_0_item = SizeGood.from_dict(
                        list_goods_type_0_item_data
                    )

                    list_goods_type_0.append(list_goods_type_0_item)

                return list_goods_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[SizeGood] | None | Unset, data)

        list_goods = _parse_list_goods(d.pop("listGoods", UNSET))

        get_api_v2_list_goods_size_nm_response_200_data = cls(
            list_goods=list_goods,
        )

        get_api_v2_list_goods_size_nm_response_200_data.additional_properties = d
        return get_api_v2_list_goods_size_nm_response_200_data

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
