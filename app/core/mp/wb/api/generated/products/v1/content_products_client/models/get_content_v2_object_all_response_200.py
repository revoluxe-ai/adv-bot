from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_content_v2_object_all_response_200_data_item import (
        GetContentV2ObjectAllResponse200DataItem,
    )


T = TypeVar("T", bound="GetContentV2ObjectAllResponse200")


@_attrs_define
class GetContentV2ObjectAllResponse200:
    """
    Attributes:
        data (list[GetContentV2ObjectAllResponse200DataItem] | Unset): Predmety
        error (bool | Unset): Flag nalichija oshibki
        error_text (str | Unset): Tekst oshibki
        additional_errors (None | str | Unset): Dopolnitel'nye oshibki
    """

    data: list[GetContentV2ObjectAllResponse200DataItem] | Unset = UNSET
    error: bool | Unset = UNSET
    error_text: str | Unset = UNSET
    additional_errors: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = []
            for data_item_data in self.data:
                data_item = data_item_data.to_dict()
                data.append(data_item)

        error = self.error

        error_text = self.error_text

        additional_errors: None | str | Unset
        if isinstance(self.additional_errors, Unset):
            additional_errors = UNSET
        else:
            additional_errors = self.additional_errors

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data
        if error is not UNSET:
            field_dict["error"] = error
        if error_text is not UNSET:
            field_dict["errorText"] = error_text
        if additional_errors is not UNSET:
            field_dict["additionalErrors"] = additional_errors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_content_v2_object_all_response_200_data_item import (
            GetContentV2ObjectAllResponse200DataItem,
        )

        d = dict(src_dict)
        _data = d.pop("data", UNSET)
        data: list[GetContentV2ObjectAllResponse200DataItem] | Unset = UNSET
        if _data is not UNSET:
            data = []
            for data_item_data in _data:
                data_item = GetContentV2ObjectAllResponse200DataItem.from_dict(
                    data_item_data
                )

                data.append(data_item)

        error = d.pop("error", UNSET)

        error_text = d.pop("errorText", UNSET)

        def _parse_additional_errors(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        additional_errors = _parse_additional_errors(d.pop("additionalErrors", UNSET))

        get_content_v2_object_all_response_200 = cls(
            data=data,
            error=error,
            error_text=error_text,
            additional_errors=additional_errors,
        )

        get_content_v2_object_all_response_200.additional_properties = d
        return get_content_v2_object_all_response_200

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
