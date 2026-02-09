from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.swagger_public_errors_cursor_input import (
        SwaggerPublicErrorsCursorInput,
    )
    from ..models.swagger_public_errors_order_v2 import SwaggerPublicErrorsOrderV2


T = TypeVar("T", bound="RequestPublicViewerPublicErrorsTableListV2")


@_attrs_define
class RequestPublicViewerPublicErrorsTableListV2:
    """
    Attributes:
        cursor (SwaggerPublicErrorsCursorInput | Unset): Paginator
        order (SwaggerPublicErrorsOrderV2 | Unset): Porjadok vydachi paketov
    """

    cursor: SwaggerPublicErrorsCursorInput | Unset = UNSET
    order: SwaggerPublicErrorsOrderV2 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cursor: dict[str, Any] | Unset = UNSET
        if not isinstance(self.cursor, Unset):
            cursor = self.cursor.to_dict()

        order: dict[str, Any] | Unset = UNSET
        if not isinstance(self.order, Unset):
            order = self.order.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cursor is not UNSET:
            field_dict["cursor"] = cursor
        if order is not UNSET:
            field_dict["order"] = order

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.swagger_public_errors_cursor_input import (
            SwaggerPublicErrorsCursorInput,
        )
        from ..models.swagger_public_errors_order_v2 import SwaggerPublicErrorsOrderV2

        d = dict(src_dict)
        _cursor = d.pop("cursor", UNSET)
        cursor: SwaggerPublicErrorsCursorInput | Unset
        if isinstance(_cursor, Unset):
            cursor = UNSET
        else:
            cursor = SwaggerPublicErrorsCursorInput.from_dict(_cursor)

        _order = d.pop("order", UNSET)
        order: SwaggerPublicErrorsOrderV2 | Unset
        if isinstance(_order, Unset):
            order = UNSET
        else:
            order = SwaggerPublicErrorsOrderV2.from_dict(_order)

        request_public_viewer_public_errors_table_list_v2 = cls(
            cursor=cursor,
            order=order,
        )

        request_public_viewer_public_errors_table_list_v2.additional_properties = d
        return request_public_viewer_public_errors_table_list_v2

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
