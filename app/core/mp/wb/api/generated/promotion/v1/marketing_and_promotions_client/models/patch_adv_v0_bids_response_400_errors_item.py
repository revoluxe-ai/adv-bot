from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PatchAdvV0BidsResponse400ErrorsItem")


@_attrs_define
class PatchAdvV0BidsResponse400ErrorsItem:
    """
    Attributes:
        detail (str | Unset): Error description
        field (str | Unset): Field containing error
    """

    detail: str | Unset = UNSET
    field: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        detail = self.detail

        field = self.field

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if detail is not UNSET:
            field_dict["detail"] = detail
        if field is not UNSET:
            field_dict["field"] = field

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        detail = d.pop("detail", UNSET)

        field = d.pop("field", UNSET)

        patch_adv_v0_bids_response_400_errors_item = cls(
            detail=detail,
            field=field,
        )

        patch_adv_v0_bids_response_400_errors_item.additional_properties = d
        return patch_adv_v0_bids_response_400_errors_item

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
