from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.models_error_table_list_public_resp_v2 import (
        ModelsErrorTableListPublicRespV2,
    )
    from ..models.response_public_viewer_public_errors_table_list_v2_additional_errors_type_0 import (
        ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0,
    )


T = TypeVar("T", bound="ResponsePublicViewerPublicErrorsTableListV2")


@_attrs_define
class ResponsePublicViewerPublicErrorsTableListV2:
    """
    Attributes:
        data (ModelsErrorTableListPublicRespV2): Dannye otveta
        error (bool): Flag oshibki
        error_text (str): Opisanie oshibki
        additional_errors (None | ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0): Dopolnitel'nye
            oshibki
    """

    data: ModelsErrorTableListPublicRespV2
    error: bool
    error_text: str
    additional_errors: (
        None | ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0
    )
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.response_public_viewer_public_errors_table_list_v2_additional_errors_type_0 import (
            ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0,
        )

        data = self.data.to_dict()

        error = self.error

        error_text = self.error_text

        additional_errors: dict[str, Any] | None
        if isinstance(
            self.additional_errors,
            ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0,
        ):
            additional_errors = self.additional_errors.to_dict()
        else:
            additional_errors = self.additional_errors

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
                "error": error,
                "errorText": error_text,
                "additionalErrors": additional_errors,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.models_error_table_list_public_resp_v2 import (
            ModelsErrorTableListPublicRespV2,
        )
        from ..models.response_public_viewer_public_errors_table_list_v2_additional_errors_type_0 import (
            ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0,
        )

        d = dict(src_dict)
        data = ModelsErrorTableListPublicRespV2.from_dict(d.pop("data"))

        error = d.pop("error")

        error_text = d.pop("errorText")

        def _parse_additional_errors(
            data: object,
        ) -> None | ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                additional_errors_type_0 = ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0.from_dict(
                    data
                )

                return additional_errors_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                None | ResponsePublicViewerPublicErrorsTableListV2AdditionalErrorsType0,
                data,
            )

        additional_errors = _parse_additional_errors(d.pop("additionalErrors"))

        response_public_viewer_public_errors_table_list_v2 = cls(
            data=data,
            error=error,
            error_text=error_text,
            additional_errors=additional_errors,
        )

        response_public_viewer_public_errors_table_list_v2.additional_properties = d
        return response_public_viewer_public_errors_table_list_v2

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
