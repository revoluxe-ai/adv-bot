from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.request_already_exists_error_data import RequestAlreadyExistsErrorData


T = TypeVar("T", bound="RequestAlreadyExistsError")


@_attrs_define
class RequestAlreadyExistsError:
    """
    Attributes:
        data (RequestAlreadyExistsErrorData | Unset): Dannye otveta
        error (bool | Unset): Flag oshibki
        error_text (str | Unset): Tekst oshibki
    """

    data: RequestAlreadyExistsErrorData | Unset = UNSET
    error: bool | Unset = UNSET
    error_text: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        error = self.error

        error_text = self.error_text

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data
        if error is not UNSET:
            field_dict["error"] = error
        if error_text is not UNSET:
            field_dict["errorText"] = error_text

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.request_already_exists_error_data import (
            RequestAlreadyExistsErrorData,
        )

        d = dict(src_dict)
        _data = d.pop("data", UNSET)
        data: RequestAlreadyExistsErrorData | Unset
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = RequestAlreadyExistsErrorData.from_dict(_data)

        error = d.pop("error", UNSET)

        error_text = d.pop("errorText", UNSET)

        request_already_exists_error = cls(
            data=data,
            error=error,
            error_text=error_text,
        )

        request_already_exists_error.additional_properties = d
        return request_already_exists_error

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
