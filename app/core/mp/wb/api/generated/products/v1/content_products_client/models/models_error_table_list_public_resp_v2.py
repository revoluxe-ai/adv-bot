from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.models_error_table_list_public_resp_v2_item import (
        ModelsErrorTableListPublicRespV2Item,
    )
    from ..models.viewer_contract_public_errors_cursor_output import (
        ViewerContractPublicErrorsCursorOutput,
    )


T = TypeVar("T", bound="ModelsErrorTableListPublicRespV2")


@_attrs_define
class ModelsErrorTableListPublicRespV2:
    """Dannye otveta

    Attributes:
        items (list[ModelsErrorTableListPublicRespV2Item]): Pakety dannyh
        cursor (ViewerContractPublicErrorsCursorOutput): Paginator
    """

    items: list[ModelsErrorTableListPublicRespV2Item]
    cursor: ViewerContractPublicErrorsCursorOutput
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        cursor = self.cursor.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "items": items,
                "cursor": cursor,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.models_error_table_list_public_resp_v2_item import (
            ModelsErrorTableListPublicRespV2Item,
        )
        from ..models.viewer_contract_public_errors_cursor_output import (
            ViewerContractPublicErrorsCursorOutput,
        )

        d = dict(src_dict)
        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = ModelsErrorTableListPublicRespV2Item.from_dict(items_item_data)

            items.append(items_item)

        cursor = ViewerContractPublicErrorsCursorOutput.from_dict(d.pop("cursor"))

        models_error_table_list_public_resp_v2 = cls(
            items=items,
            cursor=cursor,
        )

        models_error_table_list_public_resp_v2.additional_properties = d
        return models_error_table_list_public_resp_v2

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
