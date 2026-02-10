from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="SizeGoodReq")


@_attrs_define
class SizeGoodReq:
    """
    Attributes:
        nm_id (int): Artikul WB Example: 123.
        size_id (int): ID razmera. Mozhno poluchit' s pomosch'ju metodov [Poluchit' tovary s tsenami](./work-with-
            products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get) i [Poluchit' tovary s tsenami po
            artikulam](./work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/post), pole `sizeID`. V
            metodah Kontenta eto pole `chrtID` Example: 98989887.
        price (int): Tsena. Valjutu mozhno poluchit' s pomosch'ju metodov [Poluchit' tovary s tsenami](./work-with-
            products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get) i [Poluchit' tovary s tsenami po
            artikulam](./work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/post), pole
            `currencyIsoCode4217` Example: 999.
    """

    nm_id: int
    size_id: int
    price: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        size_id = self.size_id

        price = self.price

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmID": nm_id,
                "sizeID": size_id,
                "price": price,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmID")

        size_id = d.pop("sizeID")

        price = d.pop("price")

        size_good_req = cls(
            nm_id=nm_id,
            size_id=size_id,
            price=price,
        )

        size_good_req.additional_properties = d
        return size_good_req

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
