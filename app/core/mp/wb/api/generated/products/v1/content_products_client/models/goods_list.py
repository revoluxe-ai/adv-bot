from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.goods_list_sizes_item import GoodsListSizesItem


T = TypeVar("T", bound="GoodsList")


@_attrs_define
class GoodsList:
    """Razmery tovara

    Attributes:
        nm_id (int | Unset): Artikul WB Example: 98486.
        vendor_code (str | Unset): Artikul prodavtsa Example: 07326060.
        sizes (list[GoodsListSizesItem] | Unset): Razmer
        currency_iso_code_4217 (str | Unset): Valjuta, po standartu ISO 4217 Example: RUB.
        discount (int | Unset): Skidka, % Example: 30.
        club_discount (int | Unset): Skidka WB Kluba, % Example: 5.
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
    vendor_code: str | Unset = UNSET
    sizes: list[GoodsListSizesItem] | Unset = UNSET
    currency_iso_code_4217: str | Unset = UNSET
    discount: int | Unset = UNSET
    club_discount: int | Unset = UNSET
    editable_size_price: bool | Unset = UNSET
    is_bad_turnover: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        vendor_code = self.vendor_code

        sizes: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sizes, Unset):
            sizes = []
            for sizes_item_data in self.sizes:
                sizes_item = sizes_item_data.to_dict()
                sizes.append(sizes_item)

        currency_iso_code_4217 = self.currency_iso_code_4217

        discount = self.discount

        club_discount = self.club_discount

        editable_size_price = self.editable_size_price

        is_bad_turnover = self.is_bad_turnover

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if sizes is not UNSET:
            field_dict["sizes"] = sizes
        if currency_iso_code_4217 is not UNSET:
            field_dict["currencyIsoCode4217"] = currency_iso_code_4217
        if discount is not UNSET:
            field_dict["discount"] = discount
        if club_discount is not UNSET:
            field_dict["clubDiscount"] = club_discount
        if editable_size_price is not UNSET:
            field_dict["editableSizePrice"] = editable_size_price
        if is_bad_turnover is not UNSET:
            field_dict["isBadTurnover"] = is_bad_turnover

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.goods_list_sizes_item import GoodsListSizesItem

        d = dict(src_dict)
        nm_id = d.pop("nmID", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        _sizes = d.pop("sizes", UNSET)
        sizes: list[GoodsListSizesItem] | Unset = UNSET
        if _sizes is not UNSET:
            sizes = []
            for sizes_item_data in _sizes:
                sizes_item = GoodsListSizesItem.from_dict(sizes_item_data)

                sizes.append(sizes_item)

        currency_iso_code_4217 = d.pop("currencyIsoCode4217", UNSET)

        discount = d.pop("discount", UNSET)

        club_discount = d.pop("clubDiscount", UNSET)

        editable_size_price = d.pop("editableSizePrice", UNSET)

        is_bad_turnover = d.pop("isBadTurnover", UNSET)

        goods_list = cls(
            nm_id=nm_id,
            vendor_code=vendor_code,
            sizes=sizes,
            currency_iso_code_4217=currency_iso_code_4217,
            discount=discount,
            club_discount=club_discount,
            editable_size_price=editable_size_price,
            is_bad_turnover=is_bad_turnover,
        )

        goods_list.additional_properties = d
        return goods_list

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
