import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v1_get_norm_query_stats_response_item_stat import (
        V1GetNormQueryStatsResponseItemStat,
    )


T = TypeVar("T", bound="V1GetNormQueryStatsResponseItemDailyStat")


@_attrs_define
class V1GetNormQueryStatsResponseItemDailyStat:
    """
    Attributes:
        date (datetime.date): Date
        stat (Union[Unset, V1GetNormQueryStatsResponseItemStat]):
    """

    date: datetime.date
    stat: Union[Unset, "V1GetNormQueryStatsResponseItemStat"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        date = self.date.isoformat()

        stat: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.stat, Unset):
            stat = self.stat.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "date": date,
            }
        )
        if stat is not UNSET:
            field_dict["stat"] = stat

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v1_get_norm_query_stats_response_item_stat import (
            V1GetNormQueryStatsResponseItemStat,
        )

        d = src_dict.copy()
        date = isoparse(d.pop("date")).date()

        _stat = d.pop("stat", UNSET)
        stat: Union[Unset, V1GetNormQueryStatsResponseItemStat]
        if isinstance(_stat, Unset):
            stat = UNSET
        else:
            stat = V1GetNormQueryStatsResponseItemStat.from_dict(_stat)

        v1_get_norm_query_stats_response_item_daily_stat = cls(
            date=date,
            stat=stat,
        )

        v1_get_norm_query_stats_response_item_daily_stat.additional_properties = d
        return v1_get_norm_query_stats_response_item_daily_stat

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
