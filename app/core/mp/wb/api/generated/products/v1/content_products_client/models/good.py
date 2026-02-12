from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Good")


@_attrs_define
class Good:
    """
    Attributes:
        nm_id (int): Artikul WB Example: 123.
        price (int | Unset): Tsena. Valjutu mozhno poluchit' s pomosch'ju metodov [Poluchit' tovary s tsenami](./work-
            with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get) i [Poluchit' tovary s tsenami po
            artikulam](./work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/post), pole
            `currencyIsoCode4217` Example: 999.
        discount (int | Unset): Skidka, % Example: 30.
    """

    nm_id: int
    price: int | Unset = UNSET
    discount: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        price = self.price

        discount = self.discount

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmID": nm_id,
            }
        )
        if price is not UNSET:
            field_dict["price"] = price
        if discount is not UNSET:
            field_dict["discount"] = discount

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmID")

        price = d.pop("price", UNSET)

        discount = d.pop("discount", UNSET)

        good = cls(
            nm_id=nm_id,
            price=price,
            discount=discount,
        )

        good.additional_properties = d
        return good

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
