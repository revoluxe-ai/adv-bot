from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.stat_interval_interval import StatIntervalInterval
    from ..models.stats_blok_1 import StatsBlok1


T = TypeVar("T", bound="StatInterval")


@_attrs_define
class StatInterval:
    """
    Attributes:
        interval (StatIntervalInterval): Requested time range
        stats (Union[Unset, List['StatsBlok1']]): Statistics data
    """

    interval: "StatIntervalInterval"
    stats: Union[Unset, List["StatsBlok1"]] = UNSET

    def to_dict(self) -> Dict[str, Any]:
        interval = self.interval.to_dict()

        stats: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for stats_item_data in self.stats:
                stats_item = stats_item_data.to_dict()
                stats.append(stats_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "interval": interval,
            }
        )
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.stat_interval_interval import StatIntervalInterval
        from ..models.stats_blok_1 import StatsBlok1

        d = src_dict.copy()
        interval = StatIntervalInterval.from_dict(d.pop("interval"))

        stats = []
        _stats = d.pop("stats", UNSET)
        for stats_item_data in _stats or []:
            stats_item = StatsBlok1.from_dict(stats_item_data)

            stats.append(stats_item)

        stat_interval = cls(
            interval=interval,
            stats=stats,
        )

        return stat_interval
