import datetime
from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="BoosterStatsItem")


@_attrs_define
class BoosterStatsItem:
    """
    Attributes:
        date (Union[Unset, datetime.datetime]): Data, za kotoruju predostavleny dannye
        nm (Union[Unset, int]): Artikul WB
        avg_position (Union[Unset, int]): Srednjaja pozitsija tovara na stranitsah poiskovoj vydachi i kataloga
    """

    date: Union[Unset, datetime.datetime] = UNSET
    nm: Union[Unset, int] = UNSET
    avg_position: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        date: Union[Unset, str] = UNSET
        if not isinstance(self.date, Unset):
            date = self.date.isoformat()

        nm = self.nm

        avg_position = self.avg_position

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if date is not UNSET:
            field_dict["date"] = date
        if nm is not UNSET:
            field_dict["nm"] = nm
        if avg_position is not UNSET:
            field_dict["avg_position"] = avg_position

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _date = d.pop("date", UNSET)
        date: Union[Unset, datetime.datetime]
        if isinstance(_date, Unset):
            date = UNSET
        else:
            date = isoparse(_date)

        nm = d.pop("nm", UNSET)

        avg_position = d.pop("avg_position", UNSET)

        booster_stats_item = cls(
            date=date,
            nm=nm,
            avg_position=avg_position,
        )

        booster_stats_item.additional_properties = d
        return booster_stats_item

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
