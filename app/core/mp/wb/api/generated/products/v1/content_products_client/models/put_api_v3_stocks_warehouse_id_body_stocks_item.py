from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PutApiV3StocksWarehouseIdBodyStocksItem")


@_attrs_define
class PutApiV3StocksWarehouseIdBodyStocksItem:
    """
    Attributes:
        chrt_id (int | Unset): ID razmera tovara Example: 12345678.
        sku (str | Unset): Barkod. Parametr budet otkljuchen [9 fevralja](https://dev.wildberries.ru/release-
            notes?id=386) Example: SKUTest123.
        amount (int | Unset): Ostatok Example: 10.
    """

    chrt_id: int | Unset = UNSET
    sku: str | Unset = UNSET
    amount: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chrt_id = self.chrt_id

        sku = self.sku

        amount = self.amount

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if chrt_id is not UNSET:
            field_dict["chrtId"] = chrt_id
        if sku is not UNSET:
            field_dict["sku"] = sku
        if amount is not UNSET:
            field_dict["amount"] = amount

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        chrt_id = d.pop("chrtId", UNSET)

        sku = d.pop("sku", UNSET)

        amount = d.pop("amount", UNSET)

        put_api_v3_stocks_warehouse_id_body_stocks_item = cls(
            chrt_id=chrt_id,
            sku=sku,
            amount=amount,
        )

        put_api_v3_stocks_warehouse_id_body_stocks_item.additional_properties = d
        return put_api_v3_stocks_warehouse_id_body_stocks_item

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
