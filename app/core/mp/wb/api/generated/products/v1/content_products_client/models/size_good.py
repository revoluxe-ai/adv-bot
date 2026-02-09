from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SizeGood")


@_attrs_define
class SizeGood:
    """Informatsija o razmere

    Attributes:
        nm_id (int | Unset): Artikul WB Example: 123.
        size_id (int | Unset): ID razmera. Mozhno poluchit' s pomosch'ju metoda [Poluchenie spiska tovarov
            po artikulam](./work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get), pole `sizeID`. V
            metodah Kontenta eto pole `chrtID` Example: 98989887.
        vendor_code (str | Unset): Artikul prodavtsa Example: 34552332.
        price (int | Unset): Tsena Example: 1000.
        currency_iso_code_4217 (str | Unset): Valjuta, po standartu ISO 4217 Example: RUB.
        discounted_price (float | Unset): Tsena so skidkoj Example: 700.
        club_discounted_price (float | Unset): Tsena so skidkoj, vkljuchaja skidku WB Kluba Example: 665.
        discount (int | Unset): Skidka, % Example: 30.
        club_discount (int | Unset): Skidka WB Kluba, % Example: 5.
        tech_size_name (str | Unset): Razmer tovara Example: 42.
        editable_size_price (bool | Unset): Mozhno li ustanavlivat' tseny otdel'no dlja raznyh razmerov (zavisit ot
            kategorii tovara):
              - `true` — mozhno
              - `false` — nel'zja
             Example: True.
        is_bad_turnover (bool | Unset): Priznak nelikvidnogo tovara:
              - `true` — nelikvidnyj tovar s [nizkim indeksom
            ostatka](https://seller.wildberries.ru/instructions/ru/ru/material/stocks-index?categoryId=e324ce0f-9a2a-4b8d-
            8fd1-72f751b09b3b&goBackOption=prevRoute#%D1%83%D1%80%D0%BE%D0%B2%D0%BD%D0%B8-
            %D0%B8%D0%BD%D0%B4%D0%B5%D0%BA%D1%81%D0%B0-%D0%BE%D1%81%D1%82%D0%B0%D1%82%D0%BA%D0%B0)
              - Pole otsutstvuet — likvidnyj tovar
             Example: True.
    """

    nm_id: int | Unset = UNSET
    size_id: int | Unset = UNSET
    vendor_code: str | Unset = UNSET
    price: int | Unset = UNSET
    currency_iso_code_4217: str | Unset = UNSET
    discounted_price: float | Unset = UNSET
    club_discounted_price: float | Unset = UNSET
    discount: int | Unset = UNSET
    club_discount: int | Unset = UNSET
    tech_size_name: str | Unset = UNSET
    editable_size_price: bool | Unset = UNSET
    is_bad_turnover: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        size_id = self.size_id

        vendor_code = self.vendor_code

        price = self.price

        currency_iso_code_4217 = self.currency_iso_code_4217

        discounted_price = self.discounted_price

        club_discounted_price = self.club_discounted_price

        discount = self.discount

        club_discount = self.club_discount

        tech_size_name = self.tech_size_name

        editable_size_price = self.editable_size_price

        is_bad_turnover = self.is_bad_turnover

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if size_id is not UNSET:
            field_dict["sizeID"] = size_id
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if price is not UNSET:
            field_dict["price"] = price
        if currency_iso_code_4217 is not UNSET:
            field_dict["currencyIsoCode4217"] = currency_iso_code_4217
        if discounted_price is not UNSET:
            field_dict["discountedPrice"] = discounted_price
        if club_discounted_price is not UNSET:
            field_dict["clubDiscountedPrice"] = club_discounted_price
        if discount is not UNSET:
            field_dict["discount"] = discount
        if club_discount is not UNSET:
            field_dict["clubDiscount"] = club_discount
        if tech_size_name is not UNSET:
            field_dict["techSizeName"] = tech_size_name
        if editable_size_price is not UNSET:
            field_dict["editableSizePrice"] = editable_size_price
        if is_bad_turnover is not UNSET:
            field_dict["isBadTurnover"] = is_bad_turnover

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmID", UNSET)

        size_id = d.pop("sizeID", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        price = d.pop("price", UNSET)

        currency_iso_code_4217 = d.pop("currencyIsoCode4217", UNSET)

        discounted_price = d.pop("discountedPrice", UNSET)

        club_discounted_price = d.pop("clubDiscountedPrice", UNSET)

        discount = d.pop("discount", UNSET)

        club_discount = d.pop("clubDiscount", UNSET)

        tech_size_name = d.pop("techSizeName", UNSET)

        editable_size_price = d.pop("editableSizePrice", UNSET)

        is_bad_turnover = d.pop("isBadTurnover", UNSET)

        size_good = cls(
            nm_id=nm_id,
            size_id=size_id,
            vendor_code=vendor_code,
            price=price,
            currency_iso_code_4217=currency_iso_code_4217,
            discounted_price=discounted_price,
            club_discounted_price=club_discounted_price,
            discount=discount,
            club_discount=club_discount,
            tech_size_name=tech_size_name,
            editable_size_price=editable_size_price,
            is_bad_turnover=is_bad_turnover,
        )

        size_good.additional_properties = d
        return size_good

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
