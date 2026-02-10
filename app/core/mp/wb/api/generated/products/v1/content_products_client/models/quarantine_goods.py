from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="QuarantineGoods")


@_attrs_define
class QuarantineGoods:
    """
    Attributes:
        nm_id (int | Unset): Artikul WB Example: 206025152.
        size_id (int | None | Unset): Ne ispol'zuetsja
        tech_size_name (str | Unset): Ne ispol'zuetsja
        currency_iso_code_4217 (str | Unset): Valjuta po standartu ISO 4217 Example: RUB.
        new_price (float | Unset): Novaja tsena prodavtsa do skidki Example: 134.
        old_price (float | Unset): Tekuschaja tsena prodavtsa do skidki Example: 4000.
        new_discount (int | Unset): Novaja skidka prodavtsa, % Example: 25.
        old_discount (int | Unset): Tekuschaja skidka prodavtsa, % Example: 25.
        price_diff (float | Unset): Raznitsa: `newPrice` * (1 - `newDiscount` / 100) - `oldPrice` * (1 - `oldDiscount` /
            100) Example: -2899.5.
    """

    nm_id: int | Unset = UNSET
    size_id: int | None | Unset = UNSET
    tech_size_name: str | Unset = UNSET
    currency_iso_code_4217: str | Unset = UNSET
    new_price: float | Unset = UNSET
    old_price: float | Unset = UNSET
    new_discount: int | Unset = UNSET
    old_discount: int | Unset = UNSET
    price_diff: float | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        size_id: int | None | Unset
        if isinstance(self.size_id, Unset):
            size_id = UNSET
        else:
            size_id = self.size_id

        tech_size_name = self.tech_size_name

        currency_iso_code_4217 = self.currency_iso_code_4217

        new_price = self.new_price

        old_price = self.old_price

        new_discount = self.new_discount

        old_discount = self.old_discount

        price_diff = self.price_diff

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if size_id is not UNSET:
            field_dict["sizeID"] = size_id
        if tech_size_name is not UNSET:
            field_dict["techSizeName"] = tech_size_name
        if currency_iso_code_4217 is not UNSET:
            field_dict["currencyIsoCode4217"] = currency_iso_code_4217
        if new_price is not UNSET:
            field_dict["newPrice"] = new_price
        if old_price is not UNSET:
            field_dict["oldPrice"] = old_price
        if new_discount is not UNSET:
            field_dict["newDiscount"] = new_discount
        if old_discount is not UNSET:
            field_dict["oldDiscount"] = old_discount
        if price_diff is not UNSET:
            field_dict["priceDiff"] = price_diff

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmID", UNSET)

        def _parse_size_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        size_id = _parse_size_id(d.pop("sizeID", UNSET))

        tech_size_name = d.pop("techSizeName", UNSET)

        currency_iso_code_4217 = d.pop("currencyIsoCode4217", UNSET)

        new_price = d.pop("newPrice", UNSET)

        old_price = d.pop("oldPrice", UNSET)

        new_discount = d.pop("newDiscount", UNSET)

        old_discount = d.pop("oldDiscount", UNSET)

        price_diff = d.pop("priceDiff", UNSET)

        quarantine_goods = cls(
            nm_id=nm_id,
            size_id=size_id,
            tech_size_name=tech_size_name,
            currency_iso_code_4217=currency_iso_code_4217,
            new_price=new_price,
            old_price=old_price,
            new_discount=new_discount,
            old_discount=old_discount,
            price_diff=price_diff,
        )

        quarantine_goods.additional_properties = d
        return quarantine_goods

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
