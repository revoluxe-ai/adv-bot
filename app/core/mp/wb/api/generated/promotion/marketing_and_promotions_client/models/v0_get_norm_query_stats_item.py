from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

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
        stats (list[V0GetNormQueryStatsItemStat] | Unset):
    """

    advert_id: int
    nm_id: int
    stats: list[V0GetNormQueryStatsItemStat] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        stats: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for stats_item_data in self.stats:
                stats_item = stats_item_data.to_dict()
                stats.append(stats_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "advert_id": advert_id,
            "nm_id": nm_id,
        })
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.v0_get_norm_query_stats_item_stat import (
            V0GetNormQueryStatsItemStat,
        )

        d = dict(src_dict)
        advert_id = d.pop("advert_id")

        nm_id = d.pop("nm_id")

        _stats = d.pop("stats", UNSET)
        stats: list[V0GetNormQueryStatsItemStat] | Unset = UNSET
        if _stats is not UNSET:
            stats = []
            for stats_item_data in _stats:
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
