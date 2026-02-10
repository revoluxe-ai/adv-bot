from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetContentV2TagsResponse200Data")


@_attrs_define
class GetContentV2TagsResponse200Data:
    """
    Attributes:
        id (int | Unset): Chislovoj ID jarlyka
        color (str | Unset): Tsvet jarlyka
        name (str | Unset): Imja jarlyka
    """

    id: int | Unset = UNSET
    color: str | Unset = UNSET
    name: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        color = self.color

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if color is not UNSET:
            field_dict["color"] = color
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        color = d.pop("color", UNSET)

        name = d.pop("name", UNSET)

        get_content_v2_tags_response_200_data = cls(
            id=id,
            color=color,
            name=name,
        )

        get_content_v2_tags_response_200_data.additional_properties = d
        return get_content_v2_tags_response_200_data

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
