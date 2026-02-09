from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.supplier_task_metadata_buffer_type_0 import (
        SupplierTaskMetadataBufferType0,
    )


T = TypeVar("T", bound="GetApiV2BufferTasksResponse200")


@_attrs_define
class GetApiV2BufferTasksResponse200:
    """
    Attributes:
        data (None | SupplierTaskMetadataBufferType0 | Unset): Dannye otveta
        error (bool | Unset): Flag oshibki
        error_text (str | Unset): Tekst oshibki
    """

    data: None | SupplierTaskMetadataBufferType0 | Unset = UNSET
    error: bool | Unset = UNSET
    error_text: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.supplier_task_metadata_buffer_type_0 import (
            SupplierTaskMetadataBufferType0,
        )

        data: dict[str, Any] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, SupplierTaskMetadataBufferType0):
            data = self.data.to_dict()
        else:
            data = self.data

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
        from ..models.supplier_task_metadata_buffer_type_0 import (
            SupplierTaskMetadataBufferType0,
        )

        d = dict(src_dict)

        def _parse_data(data: object) -> None | SupplierTaskMetadataBufferType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_supplier_task_metadata_buffer_type_0 = (
                    SupplierTaskMetadataBufferType0.from_dict(data)
                )

                return componentsschemas_supplier_task_metadata_buffer_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SupplierTaskMetadataBufferType0 | Unset, data)

        data = _parse_data(d.pop("data", UNSET))

        error = d.pop("error", UNSET)

        error_text = d.pop("errorText", UNSET)

        get_api_v2_buffer_tasks_response_200 = cls(
            data=data,
            error=error,
            error_text=error_text,
        )

        get_api_v2_buffer_tasks_response_200.additional_properties = d
        return get_api_v2_buffer_tasks_response_200

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
