from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="GoodsListSizesItem")


@_attrs_define
class GoodsListSizesItem:
    """
    Attributes:
        size_id (int): ID razmera. V metodah Kontenta eto pole `chrtID` Example: 3123515574.
        price (int): Tsena Example: 500.
        discounted_price (float): Tsena so skidkoj Example: 350.
        club_discounted_price (float): Tsena so skidkoj, vkljuchaja skidku WB Kluba Example: 332.5.
        tech_size_name (str): Razmer tovara Example: 42.
    """

    size_id: int
    price: int
    discounted_price: float
    club_discounted_price: float
    tech_size_name: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        size_id = self.size_id

        price = self.price

        discounted_price = self.discounted_price

        club_discounted_price = self.club_discounted_price

        tech_size_name = self.tech_size_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "sizeID": size_id,
                "price": price,
                "discountedPrice": discounted_price,
                "clubDiscountedPrice": club_discounted_price,
                "techSizeName": tech_size_name,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        size_id = d.pop("sizeID")

        price = d.pop("price")

        discounted_price = d.pop("discountedPrice")

        club_discounted_price = d.pop("clubDiscountedPrice")

        tech_size_name = d.pop("techSizeName")

        goods_list_sizes_item = cls(
            size_id=size_id,
            price=price,
            discounted_price=discounted_price,
            club_discounted_price=club_discounted_price,
            tech_size_name=tech_size_name,
        )

        goods_list_sizes_item.additional_properties = d
        return goods_list_sizes_item

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
