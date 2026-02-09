from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.put_api_v3_stocks_warehouse_id_body_stocks_item import (
        PutApiV3StocksWarehouseIdBodyStocksItem,
    )


T = TypeVar("T", bound="PutApiV3StocksWarehouseIdBody")


@_attrs_define
class PutApiV3StocksWarehouseIdBody:
    """
    Attributes:
        stocks (list[PutApiV3StocksWarehouseIdBodyStocksItem]): Massiv barkodov tovarov i ih ostatkov
    """

    stocks: list[PutApiV3StocksWarehouseIdBodyStocksItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        stocks = []
        for stocks_item_data in self.stocks:
            stocks_item = stocks_item_data.to_dict()
            stocks.append(stocks_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "stocks": stocks,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.put_api_v3_stocks_warehouse_id_body_stocks_item import (
            PutApiV3StocksWarehouseIdBodyStocksItem,
        )

        d = dict(src_dict)
        stocks = []
        _stocks = d.pop("stocks")
        for stocks_item_data in _stocks:
            stocks_item = PutApiV3StocksWarehouseIdBodyStocksItem.from_dict(
                stocks_item_data
            )

            stocks.append(stocks_item)

        put_api_v3_stocks_warehouse_id_body = cls(
            stocks=stocks,
        )

        put_api_v3_stocks_warehouse_id_body.additional_properties = d
        return put_api_v3_stocks_warehouse_id_body

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
