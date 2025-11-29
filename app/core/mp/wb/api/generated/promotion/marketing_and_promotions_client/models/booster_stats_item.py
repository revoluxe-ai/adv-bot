from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="BoosterStatsItem")


@_attrs_define
class BoosterStatsItem:
    """
    Attributes:
        date (datetime.datetime | Unset): Date for which information is to be provided
        nm (int | Unset): WB article
        avg_position (int | Unset): Average position of the product on search results pages and catalog pages
    """

    date: datetime.datetime | Unset = UNSET
    nm: int | Unset = UNSET
    avg_position: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        date: str | Unset = UNSET
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
        date: datetime.datetime | Unset
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
