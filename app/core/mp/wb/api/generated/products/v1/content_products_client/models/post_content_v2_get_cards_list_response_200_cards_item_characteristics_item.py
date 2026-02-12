from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar(
    "T", bound="PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem"
)


@_attrs_define
class PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem:
    """
    Attributes:
        id (int | Unset): ID harakteristiki
        name (str | Unset): Nazvanie harakteristiki
        value (Any | Unset): Znachenie harakteristiki. Tip znachenija zavisit ot tipa harakteristiki
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    value: Any | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        value = d.pop("value", UNSET)

        post_content_v2_get_cards_list_response_200_cards_item_characteristics_item = (
            cls(
                id=id,
                name=name,
                value=value,
            )
        )

        post_content_v2_get_cards_list_response_200_cards_item_characteristics_item.additional_properties = d
        return (
            post_content_v2_get_cards_list_response_200_cards_item_characteristics_item
        )

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
