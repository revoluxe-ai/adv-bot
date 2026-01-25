from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1AutoSetExcludedBody")


@_attrs_define
class PostAdvV1AutoSetExcludedBody:
    """
    Attributes:
        excluded (list[str] | Unset): Spisok minus-fraz, do 1000 fraz
    """

    excluded: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        excluded: list[str] | Unset = UNSET
        if not isinstance(self.excluded, Unset):
            excluded = self.excluded

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if excluded is not UNSET:
            field_dict["excluded"] = excluded

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        excluded = cast(list[str], d.pop("excluded", UNSET))

        post_adv_v1_auto_set_excluded_body = cls(
            excluded=excluded,
        )

        post_adv_v1_auto_set_excluded_body.additional_properties = d
        return post_adv_v1_auto_set_excluded_body

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
