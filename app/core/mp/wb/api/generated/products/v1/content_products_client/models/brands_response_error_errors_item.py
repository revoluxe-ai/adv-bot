from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="BrandsResponseErrorErrorsItem")


@_attrs_define
class BrandsResponseErrorErrorsItem:
    """
    Attributes:
        message (str | Unset): Tekst oshibki
        location (str | Unset): Parametr, gde proizoshla oshibka
        value (Any | Unset): Znachenie parametra, gde proizoshla oshibka
    """

    message: str | Unset = UNSET
    location: str | Unset = UNSET
    value: Any | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        message = self.message

        location = self.location

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if message is not UNSET:
            field_dict["message"] = message
        if location is not UNSET:
            field_dict["location"] = location
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        message = d.pop("message", UNSET)

        location = d.pop("location", UNSET)

        value = d.pop("value", UNSET)

        brands_response_error_errors_item = cls(
            message=message,
            location=location,
            value=value,
        )

        brands_response_error_errors_item.additional_properties = d
        return brands_response_error_errors_item

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
