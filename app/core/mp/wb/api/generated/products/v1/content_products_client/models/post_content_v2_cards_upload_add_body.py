from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_cards_upload_add_body_cards_to_add_item import (
        PostContentV2CardsUploadAddBodyCardsToAddItem,
    )


T = TypeVar("T", bound="PostContentV2CardsUploadAddBody")


@_attrs_define
class PostContentV2CardsUploadAddBody:
    """
    Attributes:
        imt_id (int | Unset): `imtID` otdel'noj kartochki tovara ili gruppy
            [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov) kartochek
            tovarov, k kotoroj prisoedinjajutsja sozdavaemye kartochki
        cards_to_add (list[PostContentV2CardsUploadAddBodyCardsToAddItem] | Unset): Dobavljaemye kartochki tovarov
    """

    imt_id: int | Unset = UNSET
    cards_to_add: list[PostContentV2CardsUploadAddBodyCardsToAddItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        imt_id = self.imt_id

        cards_to_add: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.cards_to_add, Unset):
            cards_to_add = []
            for cards_to_add_item_data in self.cards_to_add:
                cards_to_add_item = cards_to_add_item_data.to_dict()
                cards_to_add.append(cards_to_add_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if imt_id is not UNSET:
            field_dict["imtID"] = imt_id
        if cards_to_add is not UNSET:
            field_dict["cardsToAdd"] = cards_to_add

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_cards_upload_add_body_cards_to_add_item import (
            PostContentV2CardsUploadAddBodyCardsToAddItem,
        )

        d = dict(src_dict)
        imt_id = d.pop("imtID", UNSET)

        _cards_to_add = d.pop("cardsToAdd", UNSET)
        cards_to_add: list[PostContentV2CardsUploadAddBodyCardsToAddItem] | Unset = (
            UNSET
        )
        if _cards_to_add is not UNSET:
            cards_to_add = []
            for cards_to_add_item_data in _cards_to_add:
                cards_to_add_item = (
                    PostContentV2CardsUploadAddBodyCardsToAddItem.from_dict(
                        cards_to_add_item_data
                    )
                )

                cards_to_add.append(cards_to_add_item)

        post_content_v2_cards_upload_add_body = cls(
            imt_id=imt_id,
            cards_to_add=cards_to_add,
        )

        post_content_v2_cards_upload_add_body.additional_properties = d
        return post_content_v2_cards_upload_add_body

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
