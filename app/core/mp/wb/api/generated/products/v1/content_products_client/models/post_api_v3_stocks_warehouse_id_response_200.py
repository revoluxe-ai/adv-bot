from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_api_v3_stocks_warehouse_id_response_200_stocks_item import (
        PostApiV3StocksWarehouseIdResponse200StocksItem,
    )


T = TypeVar("T", bound="PostApiV3StocksWarehouseIdResponse200")


@_attrs_define
class PostApiV3StocksWarehouseIdResponse200:
    """
    Attributes:
        stocks (list[PostApiV3StocksWarehouseIdResponse200StocksItem] | Unset):
    """

    stocks: list[PostApiV3StocksWarehouseIdResponse200StocksItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        stocks: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.stocks, Unset):
            stocks = []
            for stocks_item_data in self.stocks:
                stocks_item = stocks_item_data.to_dict()
                stocks.append(stocks_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if stocks is not UNSET:
            field_dict["stocks"] = stocks

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_api_v3_stocks_warehouse_id_response_200_stocks_item import (
            PostApiV3StocksWarehouseIdResponse200StocksItem,
        )

        d = dict(src_dict)
        _stocks = d.pop("stocks", UNSET)
        stocks: list[PostApiV3StocksWarehouseIdResponse200StocksItem] | Unset = UNSET
        if _stocks is not UNSET:
            stocks = []
            for stocks_item_data in _stocks:
                stocks_item = PostApiV3StocksWarehouseIdResponse200StocksItem.from_dict(
                    stocks_item_data
                )

                stocks.append(stocks_item)

        post_api_v3_stocks_warehouse_id_response_200 = cls(
            stocks=stocks,
        )

        post_api_v3_stocks_warehouse_id_response_200.additional_properties = d
        return post_api_v3_stocks_warehouse_id_response_200

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
