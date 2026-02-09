from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2CardsUpdateBodyItemSizesItem")


@_attrs_define
class PostContentV2CardsUpdateBodyItemSizesItem:
    """
    Attributes:
        chrt_id (int | Unset): ID razmera dlja dannogo artikula WB<br>
            Objazatelen k zapolneniju dlja suschestvujuschih razmerov<br>
            Dlja dobavljaemyh razmerov ne ukazyvaetsja
        tech_size (str | Unset): Razmer tovara (naprimer, XL, S, 45)
        wb_size (str | Unset): Rossijskij razmer tovara
        price (int | Unset): Tsena tovara, ₽<br>
            Ukazyvaetsja pri dobavlenii razmera
        skus (list[str] | Unset): Barkody
    """

    chrt_id: int | Unset = UNSET
    tech_size: str | Unset = UNSET
    wb_size: str | Unset = UNSET
    price: int | Unset = UNSET
    skus: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chrt_id = self.chrt_id

        tech_size = self.tech_size

        wb_size = self.wb_size

        price = self.price

        skus: list[str] | Unset = UNSET
        if not isinstance(self.skus, Unset):
            skus = self.skus

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if chrt_id is not UNSET:
            field_dict["chrtID"] = chrt_id
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
        chrt_id = d.pop("chrtID", UNSET)

        tech_size = d.pop("techSize", UNSET)

        wb_size = d.pop("wbSize", UNSET)

        price = d.pop("price", UNSET)

        skus = cast(list[str], d.pop("skus", UNSET))

        post_content_v2_cards_update_body_item_sizes_item = cls(
            chrt_id=chrt_id,
            tech_size=tech_size,
            wb_size=wb_size,
            price=price,
            skus=skus,
        )

        post_content_v2_cards_update_body_item_sizes_item.additional_properties = d
        return post_content_v2_cards_update_body_item_sizes_item

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
