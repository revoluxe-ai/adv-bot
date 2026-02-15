import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

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
        dates (List[datetime.date]): Dates for which information is to be provided
        stats (Union[Unset, List['StatsBlok2']]): Statistics data
    """

    dates: List[datetime.date]
    stats: Union[Unset, List["StatsBlok2"]] = UNSET

    def to_dict(self) -> Dict[str, Any]:
        dates = []
        for dates_item_data in self.dates:
            dates_item = dates_item_data.isoformat()
            dates.append(dates_item)

        stats: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for stats_item_data in self.stats:
                stats_item = stats_item_data.to_dict()
                stats.append(stats_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "dates": dates,
            }
        )
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.stats_blok_2 import StatsBlok2

        d = src_dict.copy()
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
