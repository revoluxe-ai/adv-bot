from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2GetCardsTrashResponse200CardsItemPhotosItem")


@_attrs_define
class PostContentV2GetCardsTrashResponse200CardsItemPhotosItem:
    """
    Attributes:
        big (str | Unset): URL foto `900x1200`
        c246x328 (str | Unset): URL foto `248x328`
        c516x688 (str | Unset): URL foto `516x688`
        square (str | Unset): URL foto `600x600`
        tm (str | Unset): URL foto `75x100`
    """

    big: str | Unset = UNSET
    c246x328: str | Unset = UNSET
    c516x688: str | Unset = UNSET
    square: str | Unset = UNSET
    tm: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        big = self.big

        c246x328 = self.c246x328

        c516x688 = self.c516x688

        square = self.square

        tm = self.tm

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if big is not UNSET:
            field_dict["big"] = big
        if c246x328 is not UNSET:
            field_dict["c246x328"] = c246x328
        if c516x688 is not UNSET:
            field_dict["c516x688"] = c516x688
        if square is not UNSET:
            field_dict["square"] = square
        if tm is not UNSET:
            field_dict["tm"] = tm

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        big = d.pop("big", UNSET)

        c246x328 = d.pop("c246x328", UNSET)

        c516x688 = d.pop("c516x688", UNSET)

        square = d.pop("square", UNSET)

        tm = d.pop("tm", UNSET)

        post_content_v2_get_cards_trash_response_200_cards_item_photos_item = cls(
            big=big,
            c246x328=c246x328,
            c516x688=c516x688,
            square=square,
            tm=tm,
        )

        post_content_v2_get_cards_trash_response_200_cards_item_photos_item.additional_properties = d
        return post_content_v2_get_cards_trash_response_200_cards_item_photos_item

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
