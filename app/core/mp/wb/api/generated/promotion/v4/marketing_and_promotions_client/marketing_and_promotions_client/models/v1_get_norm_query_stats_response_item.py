from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v1_get_norm_query_stats_response_item_daily_stat import (
        V1GetNormQueryStatsResponseItemDailyStat,
    )


T = TypeVar("T", bound="V1GetNormQueryStatsResponseItem")


@_attrs_define
class V1GetNormQueryStatsResponseItem:
    """
    Attributes:
        advert_id (int): Campaign ID
        nm_id (int): WB article
        daily_stats (Union[Unset, List['V1GetNormQueryStatsResponseItemDailyStat']]): Daily detailed statistics
    """

    advert_id: int
    nm_id: int
    daily_stats: Union[Unset, List["V1GetNormQueryStatsResponseItemDailyStat"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        daily_stats: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.daily_stats, Unset):
            daily_stats = []
            for daily_stats_item_data in self.daily_stats:
                daily_stats_item = daily_stats_item_data.to_dict()
                daily_stats.append(daily_stats_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advertId": advert_id,
                "nmId": nm_id,
            }
        )
        if daily_stats is not UNSET:
            field_dict["dailyStats"] = daily_stats

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v1_get_norm_query_stats_response_item_daily_stat import (
            V1GetNormQueryStatsResponseItemDailyStat,
        )

        d = src_dict.copy()
        advert_id = d.pop("advertId")

        nm_id = d.pop("nmId")

        daily_stats = []
        _daily_stats = d.pop("dailyStats", UNSET)
        for daily_stats_item_data in _daily_stats or []:
            daily_stats_item = V1GetNormQueryStatsResponseItemDailyStat.from_dict(
                daily_stats_item_data
            )

            daily_stats.append(daily_stats_item)

        v1_get_norm_query_stats_response_item = cls(
            advert_id=advert_id,
            nm_id=nm_id,
            daily_stats=daily_stats,
        )

        v1_get_norm_query_stats_response_item.additional_properties = d
        return v1_get_norm_query_stats_response_item

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
