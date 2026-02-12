from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.quarantine_goods import QuarantineGoods


T = TypeVar("T", bound="GetApiV2QuarantineGoodsResponse200DataType0")


@_attrs_define
class GetApiV2QuarantineGoodsResponse200DataType0:
    """Dannye otveta

    Attributes:
        quarantine_goods (list[QuarantineGoods] | Unset): Informatsija o tovarah v karantine
    """

    quarantine_goods: list[QuarantineGoods] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        quarantine_goods: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.quarantine_goods, Unset):
            quarantine_goods = []
            for quarantine_goods_item_data in self.quarantine_goods:
                quarantine_goods_item = quarantine_goods_item_data.to_dict()
                quarantine_goods.append(quarantine_goods_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if quarantine_goods is not UNSET:
            field_dict["quarantineGoods"] = quarantine_goods

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.quarantine_goods import QuarantineGoods

        d = dict(src_dict)
        _quarantine_goods = d.pop("quarantineGoods", UNSET)
        quarantine_goods: list[QuarantineGoods] | Unset = UNSET
        if _quarantine_goods is not UNSET:
            quarantine_goods = []
            for quarantine_goods_item_data in _quarantine_goods:
                quarantine_goods_item = QuarantineGoods.from_dict(
                    quarantine_goods_item_data
                )

                quarantine_goods.append(quarantine_goods_item)

        get_api_v2_quarantine_goods_response_200_data_type_0 = cls(
            quarantine_goods=quarantine_goods,
        )

        get_api_v2_quarantine_goods_response_200_data_type_0.additional_properties = d
        return get_api_v2_quarantine_goods_response_200_data_type_0

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
