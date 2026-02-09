from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.media_errors_additional_errors_type_0 import (
        MediaErrorsAdditionalErrorsType0,
    )
    from ..models.media_errors_data_type_0 import MediaErrorsDataType0


T = TypeVar("T", bound="MediaErrors")


@_attrs_define
class MediaErrors:
    """
    Example:
        {'additionalErrors': None, 'data': None, 'error': True, 'errorText': 'Error text'}

    Attributes:
        additional_errors (MediaErrorsAdditionalErrorsType0 | None | Unset): Dopolnitel'nye oshibki
        data (MediaErrorsDataType0 | None | Unset): Dannye oshibki
        error (bool | Unset): Flag oshibki
        error_text (str | Unset): Tekst oshibki
    """

    additional_errors: MediaErrorsAdditionalErrorsType0 | None | Unset = UNSET
    data: MediaErrorsDataType0 | None | Unset = UNSET
    error: bool | Unset = UNSET
    error_text: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.media_errors_additional_errors_type_0 import (
            MediaErrorsAdditionalErrorsType0,
        )
        from ..models.media_errors_data_type_0 import MediaErrorsDataType0

        additional_errors: dict[str, Any] | None | Unset
        if isinstance(self.additional_errors, Unset):
            additional_errors = UNSET
        elif isinstance(self.additional_errors, MediaErrorsAdditionalErrorsType0):
            additional_errors = self.additional_errors.to_dict()
        else:
            additional_errors = self.additional_errors

        data: dict[str, Any] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, MediaErrorsDataType0):
            data = self.data.to_dict()
        else:
            data = self.data

        error = self.error

        error_text = self.error_text

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if additional_errors is not UNSET:
            field_dict["additionalErrors"] = additional_errors
        if data is not UNSET:
            field_dict["data"] = data
        if error is not UNSET:
            field_dict["error"] = error
        if error_text is not UNSET:
            field_dict["errorText"] = error_text

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.media_errors_additional_errors_type_0 import (
            MediaErrorsAdditionalErrorsType0,
        )
        from ..models.media_errors_data_type_0 import MediaErrorsDataType0

        d = dict(src_dict)

        def _parse_additional_errors(
            data: object,
        ) -> MediaErrorsAdditionalErrorsType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                additional_errors_type_0 = MediaErrorsAdditionalErrorsType0.from_dict(
                    data
                )

                return additional_errors_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(MediaErrorsAdditionalErrorsType0 | None | Unset, data)

        additional_errors = _parse_additional_errors(d.pop("additionalErrors", UNSET))

        def _parse_data(data: object) -> MediaErrorsDataType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = MediaErrorsDataType0.from_dict(data)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(MediaErrorsDataType0 | None | Unset, data)

        data = _parse_data(d.pop("data", UNSET))

        error = d.pop("error", UNSET)

        error_text = d.pop("errorText", UNSET)

        media_errors = cls(
            additional_errors=additional_errors,
            data=data,
            error=error,
            error_text=error_text,
        )

        media_errors.additional_properties = d
        return media_errors

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
