from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GoodBufferHistory")


@_attrs_define
class GoodBufferHistory:
    """
    Attributes:
        nm_id (int | Unset): Artikul WB Example: 544833232.
        vendor_code (str | Unset): Artikul prodavtsa Example: 34552332.
        size_id (int | Unset): ID razmera. V metodah Kontenta eto pole `chrtID` Example: 54483342.
        tech_size_name (str | Unset): Razmer Example: XXL.
        price (int | Unset): Tsena Example: 1500.
        currency_iso_code_4217 (str | Unset): Valjuta, po standartu ISO 4217 Example: RUB.
        discount (int | Unset): Skidka, % Example: 25.
        club_discount (int | Unset): Skidka WB Kluba, % Example: 5.
        status (int | Unset): Status tovara: `1` — v obrabotke
             Example: 1.
        error_text (None | str | Unset): Tekst oshibki
    """

    nm_id: int | Unset = UNSET
    vendor_code: str | Unset = UNSET
    size_id: int | Unset = UNSET
    tech_size_name: str | Unset = UNSET
    price: int | Unset = UNSET
    currency_iso_code_4217: str | Unset = UNSET
    discount: int | Unset = UNSET
    club_discount: int | Unset = UNSET
    status: int | Unset = UNSET
    error_text: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        vendor_code = self.vendor_code

        size_id = self.size_id

        tech_size_name = self.tech_size_name

        price = self.price

        currency_iso_code_4217 = self.currency_iso_code_4217

        discount = self.discount

        club_discount = self.club_discount

        status = self.status

        error_text: None | str | Unset
        if isinstance(self.error_text, Unset):
            error_text = UNSET
        else:
            error_text = self.error_text

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if size_id is not UNSET:
            field_dict["sizeID"] = size_id
        if tech_size_name is not UNSET:
            field_dict["techSizeName"] = tech_size_name
        if price is not UNSET:
            field_dict["price"] = price
        if currency_iso_code_4217 is not UNSET:
            field_dict["currencyIsoCode4217"] = currency_iso_code_4217
        if discount is not UNSET:
            field_dict["discount"] = discount
        if club_discount is not UNSET:
            field_dict["clubDiscount"] = club_discount
        if status is not UNSET:
            field_dict["status"] = status
        if error_text is not UNSET:
            field_dict["errorText"] = error_text

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmID", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        size_id = d.pop("sizeID", UNSET)

        tech_size_name = d.pop("techSizeName", UNSET)

        price = d.pop("price", UNSET)

        currency_iso_code_4217 = d.pop("currencyIsoCode4217", UNSET)

        discount = d.pop("discount", UNSET)

        club_discount = d.pop("clubDiscount", UNSET)

        status = d.pop("status", UNSET)

        def _parse_error_text(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error_text = _parse_error_text(d.pop("errorText", UNSET))

        good_buffer_history = cls(
            nm_id=nm_id,
            vendor_code=vendor_code,
            size_id=size_id,
            tech_size_name=tech_size_name,
            price=price,
            currency_iso_code_4217=currency_iso_code_4217,
            discount=discount,
            club_discount=club_discount,
            status=status,
            error_text=error_text,
        )

        good_buffer_history.additional_properties = d
        return good_buffer_history

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
