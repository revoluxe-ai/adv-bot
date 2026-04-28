from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_get_norm_query_stats_item_stat import V0GetNormQueryStatsItemStat


T = TypeVar("T", bound="V0GetNormQueryStatsItem")


@_attrs_define
class V0GetNormQueryStatsItem:
    """
    Attributes:
        advert_id (int): Campaign ID
        nm_id (int): WB article
        stats (Union[Unset, List['V0GetNormQueryStatsItemStat']]):
    """

    advert_id: int
    nm_id: int
    stats: Union[Unset, List["V0GetNormQueryStatsItemStat"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        stats: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for stats_item_data in self.stats:
                stats_item = stats_item_data.to_dict()
                stats.append(stats_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nm_id": nm_id,
            }
        )
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_get_norm_query_stats_item_stat import (
            V0GetNormQueryStatsItemStat,
        )

        d = src_dict.copy()
        advert_id = d.pop("advert_id")

        nm_id = d.pop("nm_id")

        stats = []
        _stats = d.pop("stats", UNSET)
        for stats_item_data in _stats or []:
            stats_item = V0GetNormQueryStatsItemStat.from_dict(stats_item_data)

            stats.append(stats_item)

        v0_get_norm_query_stats_item = cls(
            advert_id=advert_id,
            nm_id=nm_id,
            stats=stats,
        )

        v0_get_norm_query_stats_item.additional_properties = d
        return v0_get_norm_query_stats_item

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
