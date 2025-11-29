from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PatchAdvV0AuctionNmsResponse200NmsItemNms")


@_attrs_define
class PatchAdvV0AuctionNmsResponse200NmsItemNms:
    """Product cards

    Attributes:
        added (list[int]): Added product cards
        deleted (list[int]): Deleted product cards
    """

    added: list[int]
    deleted: list[int]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        added = self.added

        deleted = self.deleted

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "added": added,
            "deleted": deleted,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        added = cast(list[int], d.pop("added"))

        deleted = cast(list[int], d.pop("deleted"))

        patch_adv_v0_auction_nms_response_200_nms_item_nms = cls(
            added=added,
            deleted=deleted,
        )

        patch_adv_v0_auction_nms_response_200_nms_item_nms.additional_properties = d
        return patch_adv_v0_auction_nms_response_200_nms_item_nms

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
