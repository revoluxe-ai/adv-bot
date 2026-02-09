from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SwaggerPublicErrorsOrderV2")


@_attrs_define
class SwaggerPublicErrorsOrderV2:
    """Porjadok vydachi paketov

    Attributes:
        ascending (bool | Unset): - `false` — sortirovka po ubyvaniju
            - `true` — sortirovka po vozrastaniju
             Default: True.
    """

    ascending: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ascending = self.ascending

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if ascending is not UNSET:
            field_dict["ascending"] = ascending

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        ascending = d.pop("ascending", UNSET)

        swagger_public_errors_order_v2 = cls(
            ascending=ascending,
        )

        swagger_public_errors_order_v2.additional_properties = d
        return swagger_public_errors_order_v2

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
