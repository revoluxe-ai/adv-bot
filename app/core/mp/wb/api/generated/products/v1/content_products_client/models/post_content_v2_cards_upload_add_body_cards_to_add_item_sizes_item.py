from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2CardsUploadAddBodyCardsToAddItemSizesItem")


@_attrs_define
class PostContentV2CardsUploadAddBodyCardsToAddItemSizesItem:
    """
    Attributes:
        tech_size (str | Unset): Razmer tovara (naprimer, XL, 45)
        wb_size (str | Unset): Rossijskij razmer tovara
        price (int | Unset): Tsena tovara
        skus (list[str] | Unset): Barkod. Esli ne ukazat', sgeneriruetsja avtomaticheski
    """

    tech_size: str | Unset = UNSET
    wb_size: str | Unset = UNSET
    price: int | Unset = UNSET
    skus: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        tech_size = self.tech_size

        wb_size = self.wb_size

        price = self.price

        skus: list[str] | Unset = UNSET
        if not isinstance(self.skus, Unset):
            skus = self.skus

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if tech_size is not UNSET:
            field_dict["techSize"] = tech_size
        if wb_size is not UNSET:
            field_dict["wbSize"] = wb_size
        if price is not UNSET:
            field_dict["price"] = price
        if skus is not UNSET:
            field_dict["skus"] = skus

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        tech_size = d.pop("techSize", UNSET)

        wb_size = d.pop("wbSize", UNSET)

        price = d.pop("price", UNSET)

        skus = cast(list[str], d.pop("skus", UNSET))

        post_content_v2_cards_upload_add_body_cards_to_add_item_sizes_item = cls(
            tech_size=tech_size,
            wb_size=wb_size,
            price=price,
            skus=skus,
        )

        post_content_v2_cards_upload_add_body_cards_to_add_item_sizes_item.additional_properties = d
        return post_content_v2_cards_upload_add_body_cards_to_add_item_sizes_item

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
