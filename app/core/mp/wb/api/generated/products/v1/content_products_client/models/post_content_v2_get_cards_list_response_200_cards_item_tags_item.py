from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2GetCardsListResponse200CardsItemTagsItem")


@_attrs_define
class PostContentV2GetCardsListResponse200CardsItemTagsItem:
    """
    Attributes:
        id (int | Unset): ID jarlyka
        name (str | Unset): Nazvanie jarlyka
        color (str | Unset): Tsvet jarlyka. <br>
            Dostupnye tsveta:
            - `D1CFD7` — seryj
            - `FEE0E0` — krasnyj
            - `ECDAFF` — fioletovyj
            - `E4EAFF` — sinij
            - `DEF1DD` — zelenyj
            - `FFECC7` — zheltyj
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    color: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        color = self.color

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if color is not UNSET:
            field_dict["color"] = color

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        color = d.pop("color", UNSET)

        post_content_v2_get_cards_list_response_200_cards_item_tags_item = cls(
            id=id,
            name=name,
            color=color,
        )

        post_content_v2_get_cards_list_response_200_cards_item_tags_item.additional_properties = d
        return post_content_v2_get_cards_list_response_200_cards_item_tags_item

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
