import datetime
from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.stats_blok_2 import StatsBlok2


T = TypeVar("T", bound="StatDate")


@_attrs_define
class StatDate:
    """
    Attributes:
        dates (list[datetime.date]): Daty, za kotorye nuzhno poluchit' informatsiju
        stats (Union[Unset, list['StatsBlok2']]): Blok statistiki
    """

    dates: list[datetime.date]
    stats: Union[Unset, list["StatsBlok2"]] = UNSET

    def to_dict(self) -> dict[str, Any]:
        dates = []
        for dates_item_data in self.dates:
            dates_item = dates_item_data.isoformat()
            dates.append(dates_item)

        stats: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for stats_item_data in self.stats:
                stats_item = stats_item_data.to_dict()
                stats.append(stats_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "dates": dates,
            }
        )
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.stats_blok_2 import StatsBlok2

        d = dict(src_dict)
        dates = []
        _dates = d.pop("dates")
        for dates_item_data in _dates:
            dates_item = isoparse(dates_item_data).date()

            dates.append(dates_item)

        stats = []
        _stats = d.pop("stats", UNSET)
        for stats_item_data in _stats or []:
            stats_item = StatsBlok2.from_dict(stats_item_data)

            stats.append(stats_item)

        stat_date = cls(
            dates=dates,
            stats=stats,
        )

        return stat_date
