from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.response_body_content_error_400_additional_errors_type_0 import (
        ResponseBodyContentError400AdditionalErrorsType0,
    )
    from ..models.response_body_content_error_400_data_type_0 import (
        ResponseBodyContentError400DataType0,
    )


T = TypeVar("T", bound="ResponseBodyContentError400")


@_attrs_define
class ResponseBodyContentError400:
    """
    Attributes:
        data (None | ResponseBodyContentError400DataType0 | Unset): Dannye oshibki
        error (bool | Unset): Flag oshibki
        error_text (str | Unset): Tekst oshibki
        additional_errors (None | ResponseBodyContentError400AdditionalErrorsType0 | Unset): Dopolnitel'nye oshibki
    """

    data: None | ResponseBodyContentError400DataType0 | Unset = UNSET
    error: bool | Unset = UNSET
    error_text: str | Unset = UNSET
    additional_errors: (
        None | ResponseBodyContentError400AdditionalErrorsType0 | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.response_body_content_error_400_additional_errors_type_0 import (
            ResponseBodyContentError400AdditionalErrorsType0,
        )
        from ..models.response_body_content_error_400_data_type_0 import (
            ResponseBodyContentError400DataType0,
        )

        data: dict[str, Any] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, ResponseBodyContentError400DataType0):
            data = self.data.to_dict()
        else:
            data = self.data

        error = self.error

        error_text = self.error_text

        additional_errors: dict[str, Any] | None | Unset
        if isinstance(self.additional_errors, Unset):
            additional_errors = UNSET
        elif isinstance(
            self.additional_errors, ResponseBodyContentError400AdditionalErrorsType0
        ):
            additional_errors = self.additional_errors.to_dict()
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
        from ..models.response_body_content_error_400_additional_errors_type_0 import (
            ResponseBodyContentError400AdditionalErrorsType0,
        )
        from ..models.response_body_content_error_400_data_type_0 import (
            ResponseBodyContentError400DataType0,
        )

        d = dict(src_dict)

        def _parse_data(
            data: object,
        ) -> None | ResponseBodyContentError400DataType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = ResponseBodyContentError400DataType0.from_dict(data)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ResponseBodyContentError400DataType0 | Unset, data)

        data = _parse_data(d.pop("data", UNSET))

        error = d.pop("error", UNSET)

        error_text = d.pop("errorText", UNSET)

        def _parse_additional_errors(
            data: object,
        ) -> None | ResponseBodyContentError400AdditionalErrorsType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                additional_errors_type_0 = (
                    ResponseBodyContentError400AdditionalErrorsType0.from_dict(data)
                )

                return additional_errors_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                None | ResponseBodyContentError400AdditionalErrorsType0 | Unset, data
            )

        additional_errors = _parse_additional_errors(d.pop("additionalErrors", UNSET))

        response_body_content_error_400 = cls(
            data=data,
            error=error,
            error_text=error_text,
            additional_errors=additional_errors,
        )

        response_body_content_error_400.additional_properties = d
        return response_body_content_error_400

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
