import datetime
from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.daily_stats_2_item_app_type_stats_item import (
        DailyStats2ItemAppTypeStatsItem,
    )


T = TypeVar("T", bound="DailyStats2Item")


@_attrs_define
class DailyStats2Item:
    """
    Attributes:
        date (Union[Unset, datetime.datetime]): Data
        app_type_stats (Union[Unset, list['DailyStats2ItemAppTypeStatsItem']]): Statistika po platformam
    """

    date: Union[Unset, datetime.datetime] = UNSET
    app_type_stats: Union[Unset, list["DailyStats2ItemAppTypeStatsItem"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        date: Union[Unset, str] = UNSET
        if not isinstance(self.date, Unset):
            date = self.date.isoformat()

        app_type_stats: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.app_type_stats, Unset):
            app_type_stats = []
            for app_type_stats_item_data in self.app_type_stats:
                app_type_stats_item = app_type_stats_item_data.to_dict()
                app_type_stats.append(app_type_stats_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if date is not UNSET:
            field_dict["date"] = date
        if app_type_stats is not UNSET:
            field_dict["app_type_stats"] = app_type_stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.daily_stats_2_item_app_type_stats_item import (
            DailyStats2ItemAppTypeStatsItem,
        )

        d = dict(src_dict)
        _date = d.pop("date", UNSET)
        date: Union[Unset, datetime.datetime]
        if isinstance(_date, Unset):
            date = UNSET
        else:
            date = isoparse(_date)

        app_type_stats = []
        _app_type_stats = d.pop("app_type_stats", UNSET)
        for app_type_stats_item_data in _app_type_stats or []:
            app_type_stats_item = DailyStats2ItemAppTypeStatsItem.from_dict(
                app_type_stats_item_data
            )

            app_type_stats.append(app_type_stats_item)

        daily_stats_2_item = cls(
            date=date,
            app_type_stats=app_type_stats,
        )

        daily_stats_2_item.additional_properties = d
        return daily_stats_2_item

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
