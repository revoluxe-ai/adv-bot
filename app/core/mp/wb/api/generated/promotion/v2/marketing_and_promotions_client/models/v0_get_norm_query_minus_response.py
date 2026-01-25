from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.v0_get_norm_query_minus_response_item import (
        V0GetNormQueryMinusResponseItem,
    )


T = TypeVar("T", bound="V0GetNormQueryMinusResponse")


@_attrs_define
class V0GetNormQueryMinusResponse:
    """
    Attributes:
        items (list[V0GetNormQueryMinusResponseItem]):
    """

    items: list[V0GetNormQueryMinusResponseItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "items": items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.v0_get_norm_query_minus_response_item import (
            V0GetNormQueryMinusResponseItem,
        )

        d = dict(src_dict)
        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = V0GetNormQueryMinusResponseItem.from_dict(items_item_data)

            items.append(items_item)

        v0_get_norm_query_minus_response = cls(
            items=items,
        )

        v0_get_norm_query_minus_response.additional_properties = d
        return v0_get_norm_query_minus_response

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
