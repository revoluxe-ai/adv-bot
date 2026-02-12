from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetContentV2ObjectAllResponse200DataItem")


@_attrs_define
class GetContentV2ObjectAllResponse200DataItem:
    """
    Attributes:
        subject_id (int | Unset): ID predmeta
        parent_id (int | Unset): ID roditel'skoj kategorii
        subject_name (str | Unset): Nazvanie predmeta
        parent_name (str | Unset): Nazvanie roditel'skoj kategorii
    """

    subject_id: int | Unset = UNSET
    parent_id: int | Unset = UNSET
    subject_name: str | Unset = UNSET
    parent_name: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subject_id = self.subject_id

        parent_id = self.parent_id

        subject_name = self.subject_name

        parent_name = self.parent_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if subject_id is not UNSET:
            field_dict["subjectID"] = subject_id
        if parent_id is not UNSET:
            field_dict["parentID"] = parent_id
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if parent_name is not UNSET:
            field_dict["parentName"] = parent_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        subject_id = d.pop("subjectID", UNSET)

        parent_id = d.pop("parentID", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        parent_name = d.pop("parentName", UNSET)

        get_content_v2_object_all_response_200_data_item = cls(
            subject_id=subject_id,
            parent_id=parent_id,
            subject_name=subject_name,
            parent_name=parent_name,
        )

        get_content_v2_object_all_response_200_data_item.additional_properties = d
        return get_content_v2_object_all_response_200_data_item

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
