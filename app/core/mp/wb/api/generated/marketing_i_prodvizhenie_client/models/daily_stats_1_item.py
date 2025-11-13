import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.daily_stats_1_item_app_type_stats_item import DailyStats1ItemAppTypeStatsItem


T = TypeVar("T", bound="DailyStats1Item")


@_attrs_define
class DailyStats1Item:
    """
    Attributes:
        date (Union[Unset, datetime.datetime]): Data
        app_type_stats (Union[Unset, List['DailyStats1ItemAppTypeStatsItem']]): Statistika po platformam
    """

    date: Union[Unset, datetime.datetime] = UNSET
    app_type_stats: Union[Unset, List["DailyStats1ItemAppTypeStatsItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        date: Union[Unset, str] = UNSET
        if not isinstance(self.date, Unset):
            date = self.date.isoformat()

        app_type_stats: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.app_type_stats, Unset):
            app_type_stats = []
            for app_type_stats_item_data in self.app_type_stats:
                app_type_stats_item = app_type_stats_item_data.to_dict()
                app_type_stats.append(app_type_stats_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if date is not UNSET:
            field_dict["date"] = date
        if app_type_stats is not UNSET:
            field_dict["app_type_stats"] = app_type_stats

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.daily_stats_1_item_app_type_stats_item import DailyStats1ItemAppTypeStatsItem

        d = src_dict.copy()
        _date = d.pop("date", UNSET)
        date: Union[Unset, datetime.datetime]
        if isinstance(_date, Unset):
            date = UNSET
        else:
            date = isoparse(_date)

        app_type_stats = []
        _app_type_stats = d.pop("app_type_stats", UNSET)
        for app_type_stats_item_data in _app_type_stats or []:
            app_type_stats_item = DailyStats1ItemAppTypeStatsItem.from_dict(app_type_stats_item_data)

            app_type_stats.append(app_type_stats_item)

        daily_stats_1_item = cls(
            date=date,
            app_type_stats=app_type_stats,
        )

        daily_stats_1_item.additional_properties = d
        return daily_stats_1_item

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
