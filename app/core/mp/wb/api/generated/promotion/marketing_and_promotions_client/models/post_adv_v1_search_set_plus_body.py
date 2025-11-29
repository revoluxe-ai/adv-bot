from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1SearchSetPlusBody")


@_attrs_define
class PostAdvV1SearchSetPlusBody:
    """
    Attributes:
        pluse (list[str] | Unset): Fixed phrase list (max. 100)
    """

    pluse: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        pluse: list[str] | Unset = UNSET
        if not isinstance(self.pluse, Unset):
            pluse = self.pluse

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if pluse is not UNSET:
            field_dict["pluse"] = pluse

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        pluse = cast(list[str], d.pop("pluse", UNSET))

        post_adv_v1_search_set_plus_body = cls(
            pluse=pluse,
        )

        post_adv_v1_search_set_plus_body.additional_properties = d
        return post_adv_v1_search_set_plus_body

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
