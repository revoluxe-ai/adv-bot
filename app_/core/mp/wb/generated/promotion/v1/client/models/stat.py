from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.stats_blok_1 import StatsBlok1


T = TypeVar("T", bound="Stat")


@_attrs_define
class Stat:
    """
    Attributes:
        stats (Union[Unset, list['StatsBlok1']]): Blok statistiki
    """

    stats: Union[Unset, list["StatsBlok1"]] = UNSET

    def to_dict(self) -> dict[str, Any]:
        stats: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for stats_item_data in self.stats:
                stats_item = stats_item_data.to_dict()
                stats.append(stats_item)

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.stats_blok_1 import StatsBlok1

        d = dict(src_dict)
        stats = []
        _stats = d.pop("stats", UNSET)
        for stats_item_data in _stats or []:
            stats_item = StatsBlok1.from_dict(stats_item_data)

            stats.append(stats_item)

        stat = cls(
            stats=stats,
        )

        return stat
