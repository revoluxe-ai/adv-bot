from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2CardsRecoverBody")


@_attrs_define
class PostContentV2CardsRecoverBody:
    """
    Attributes:
        nm_i_ds (list[int] | Unset): Artikuly WB
    """

    nm_i_ds: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_i_ds: list[int] | Unset = UNSET
        if not isinstance(self.nm_i_ds, Unset):
            nm_i_ds = self.nm_i_ds

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_i_ds is not UNSET:
            field_dict["nmIDs"] = nm_i_ds

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_i_ds = cast(list[int], d.pop("nmIDs", UNSET))

        post_content_v2_cards_recover_body = cls(
            nm_i_ds=nm_i_ds,
        )

        post_content_v2_cards_recover_body.additional_properties = d
        return post_content_v2_cards_recover_body

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
