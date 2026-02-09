from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_get_cards_trash_response_200_cards_item import (
        PostContentV2GetCardsTrashResponse200CardsItem,
    )
    from ..models.post_content_v2_get_cards_trash_response_200_cursor import (
        PostContentV2GetCardsTrashResponse200Cursor,
    )


T = TypeVar("T", bound="PostContentV2GetCardsTrashResponse200")


@_attrs_define
class PostContentV2GetCardsTrashResponse200:
    """
    Attributes:
        cards (list[PostContentV2GetCardsTrashResponse200CardsItem] | Unset): Massiv kartochek tovarov
        cursor (PostContentV2GetCardsTrashResponse200Cursor | Unset): Paginator
    """

    cards: list[PostContentV2GetCardsTrashResponse200CardsItem] | Unset = UNSET
    cursor: PostContentV2GetCardsTrashResponse200Cursor | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cards: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.cards, Unset):
            cards = []
            for cards_item_data in self.cards:
                cards_item = cards_item_data.to_dict()
                cards.append(cards_item)

        cursor: dict[str, Any] | Unset = UNSET
        if not isinstance(self.cursor, Unset):
            cursor = self.cursor.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cards is not UNSET:
            field_dict["cards"] = cards
        if cursor is not UNSET:
            field_dict["cursor"] = cursor

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_get_cards_trash_response_200_cards_item import (
            PostContentV2GetCardsTrashResponse200CardsItem,
        )
        from ..models.post_content_v2_get_cards_trash_response_200_cursor import (
            PostContentV2GetCardsTrashResponse200Cursor,
        )

        d = dict(src_dict)
        _cards = d.pop("cards", UNSET)
        cards: list[PostContentV2GetCardsTrashResponse200CardsItem] | Unset = UNSET
        if _cards is not UNSET:
            cards = []
            for cards_item_data in _cards:
                cards_item = PostContentV2GetCardsTrashResponse200CardsItem.from_dict(
                    cards_item_data
                )

                cards.append(cards_item)

        _cursor = d.pop("cursor", UNSET)
        cursor: PostContentV2GetCardsTrashResponse200Cursor | Unset
        if isinstance(_cursor, Unset):
            cursor = UNSET
        else:
            cursor = PostContentV2GetCardsTrashResponse200Cursor.from_dict(_cursor)

        post_content_v2_get_cards_trash_response_200 = cls(
            cards=cards,
            cursor=cursor,
        )

        post_content_v2_get_cards_trash_response_200.additional_properties = d
        return post_content_v2_get_cards_trash_response_200

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
