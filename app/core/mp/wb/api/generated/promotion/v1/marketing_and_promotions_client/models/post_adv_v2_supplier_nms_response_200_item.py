from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV2SupplierNmsResponse200Item")


@_attrs_define
class PostAdvV2SupplierNmsResponse200Item:
    """
    Attributes:
        title (str | Unset): Product name Example: Pled.
        nm (int | Unset): WB article Example: 146168367.
        subject_id (int | Unset): Subject ID Example: 765.
    """

    title: str | Unset = UNSET
    nm: int | Unset = UNSET
    subject_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        nm = self.nm

        subject_id = self.subject_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if title is not UNSET:
            field_dict["title"] = title
        if nm is not UNSET:
            field_dict["nm"] = nm
        if subject_id is not UNSET:
            field_dict["subjectId"] = subject_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title", UNSET)

        nm = d.pop("nm", UNSET)

        subject_id = d.pop("subjectId", UNSET)

        post_adv_v2_supplier_nms_response_200_item = cls(
            title=title,
            nm=nm,
            subject_id=subject_id,
        )

        post_adv_v2_supplier_nms_response_200_item.additional_properties = d
        return post_adv_v2_supplier_nms_response_200_item

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
