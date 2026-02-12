from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2TagBody")


@_attrs_define
class PostContentV2TagBody:
    """
    Attributes:
        color (str | Unset): Tsvet jarlyka.

            Dostupnye tsveta:
              - `D1CFD7` — seryj
              - `FEE0E0` — krasnyj
              - `ECDAFF` — fioletovyj
              - `E4EAFF` — sinij
              - `DEF1DD` — zelenyj
              - `FFECC7` — zheltyj
             Example: D1CFD7.
        name (str | Unset): Imja jarlyka Example: Sale.
    """

    color: str | Unset = UNSET
    name: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        color = self.color

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if color is not UNSET:
            field_dict["color"] = color
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        color = d.pop("color", UNSET)

        name = d.pop("name", UNSET)

        post_content_v2_tag_body = cls(
            color=color,
            name=name,
        )

        post_content_v2_tag_body.additional_properties = d
        return post_content_v2_tag_body

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
