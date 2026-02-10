from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetContentV2DirectoryTnvedResponse200DataItem")


@_attrs_define
class GetContentV2DirectoryTnvedResponse200DataItem:
    """
    Attributes:
        tnved (str | Unset): TNVED-kod
        is_kiz (bool | Unset): - `true` - kod markirovki trebuetsja
            - `false` - kod markirovki ne trebuetsja
    """

    tnved: str | Unset = UNSET
    is_kiz: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        tnved = self.tnved

        is_kiz = self.is_kiz

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if tnved is not UNSET:
            field_dict["tnved"] = tnved
        if is_kiz is not UNSET:
            field_dict["isKiz"] = is_kiz

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        tnved = d.pop("tnved", UNSET)

        is_kiz = d.pop("isKiz", UNSET)

        get_content_v2_directory_tnved_response_200_data_item = cls(
            tnved=tnved,
            is_kiz=is_kiz,
        )

        get_content_v2_directory_tnved_response_200_data_item.additional_properties = d
        return get_content_v2_directory_tnved_response_200_data_item

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
