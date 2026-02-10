from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.good_history import GoodHistory


T = TypeVar("T", bound="GetApiV2HistoryGoodsTaskResponse200Data")


@_attrs_define
class GetApiV2HistoryGoodsTaskResponse200Data:
    """Dannye otveta

    Attributes:
        upload_id (int | Unset): ID zagruzki Example: 3235236546.
        history_goods (list[GoodHistory] | Unset): Informatsija o tovarah v zagruzke
    """

    upload_id: int | Unset = UNSET
    history_goods: list[GoodHistory] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        upload_id = self.upload_id

        history_goods: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.history_goods, Unset):
            history_goods = []
            for history_goods_item_data in self.history_goods:
                history_goods_item = history_goods_item_data.to_dict()
                history_goods.append(history_goods_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if upload_id is not UNSET:
            field_dict["uploadID"] = upload_id
        if history_goods is not UNSET:
            field_dict["historyGoods"] = history_goods

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.good_history import GoodHistory

        d = dict(src_dict)
        upload_id = d.pop("uploadID", UNSET)

        _history_goods = d.pop("historyGoods", UNSET)
        history_goods: list[GoodHistory] | Unset = UNSET
        if _history_goods is not UNSET:
            history_goods = []
            for history_goods_item_data in _history_goods:
                history_goods_item = GoodHistory.from_dict(history_goods_item_data)

                history_goods.append(history_goods_item)

        get_api_v2_history_goods_task_response_200_data = cls(
            upload_id=upload_id,
            history_goods=history_goods,
        )

        get_api_v2_history_goods_task_response_200_data.additional_properties = d
        return get_api_v2_history_goods_task_response_200_data

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
