from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_keywords_statistic import V0KeywordsStatistic


T = TypeVar("T", bound="V0KeywordsStatistics")


@_attrs_define
class V0KeywordsStatistics:
    """
    Attributes:
        date (datetime.date): Date
        stats (list[V0KeywordsStatistic]):
    """

    date: datetime.date
    stats: list[V0KeywordsStatistic]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.v0_keywords_statistic import V0KeywordsStatistic

        date = self.date.isoformat()

        stats = []
        for stats_item_data in self.stats:
            stats_item = stats_item_data.to_dict()
            stats.append(stats_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "date": date,
            "stats": stats,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.v0_keywords_statistic import V0KeywordsStatistic

        d = dict(src_dict)
        date = isoparse(d.pop("date")).date()

        stats = []
        _stats = d.pop("stats")
        for stats_item_data in _stats:
            stats_item = V0KeywordsStatistic.from_dict(stats_item_data)

            stats.append(stats_item)

        v0_keywords_statistics = cls(
            date=date,
            stats=stats,
        )

        v0_keywords_statistics.additional_properties = d
        return v0_keywords_statistics

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
