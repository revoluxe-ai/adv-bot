from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PatchAdvV0AuctionNmsBodyNmsItemNms")


@_attrs_define
class PatchAdvV0AuctionNmsBodyNmsItemNms:
    """Product cards. Maximum of 50 products per campaign

    Attributes:
        add (Any | Unset): The product cards that need to be added
        delete (list[int] | Unset): The product cards that need to be deleted
    """

    add: Any | Unset = UNSET
    delete: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        add = self.add

        delete: list[int] | Unset = UNSET
        if not isinstance(self.delete, Unset):
            delete = self.delete

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if add is not UNSET:
            field_dict["add"] = add
        if delete is not UNSET:
            field_dict["delete"] = delete

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        add = d.pop("add", UNSET)

        delete = cast(list[int], d.pop("delete", UNSET))

        patch_adv_v0_auction_nms_body_nms_item_nms = cls(
            add=add,
            delete=delete,
        )

        patch_adv_v0_auction_nms_body_nms_item_nms.additional_properties = d
        return patch_adv_v0_auction_nms_body_nms_item_nms

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
