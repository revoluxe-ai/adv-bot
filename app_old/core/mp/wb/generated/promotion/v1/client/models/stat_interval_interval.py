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

T = TypeVar("T", bound="StatIntervalInterval")


@_attrs_define
class StatIntervalInterval:
    """Period

    Attributes:
        begin (Union[Unset, datetime.date]): Nachalo perioda
        end (Union[Unset, datetime.date]): Konets perioda
    """

    begin: Union[Unset, datetime.date] = UNSET
    end: Union[Unset, datetime.date] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        begin: Union[Unset, str] = UNSET
        if not isinstance(self.begin, Unset):
            begin = self.begin.isoformat()

        end: Union[Unset, str] = UNSET
        if not isinstance(self.end, Unset):
            end = self.end.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if begin is not UNSET:
            field_dict["begin"] = begin
        if end is not UNSET:
            field_dict["end"] = end

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _begin = d.pop("begin", UNSET)
        begin: Union[Unset, datetime.date]
        if isinstance(_begin, Unset):
            begin = UNSET
        else:
            begin = isoparse(_begin).date()

        _end = d.pop("end", UNSET)
        end: Union[Unset, datetime.date]
        if isinstance(_end, Unset):
            end = UNSET
        else:
            end = isoparse(_end).date()

        stat_interval_interval = cls(
            begin=begin,
            end=end,
        )

        stat_interval_interval.additional_properties = d
        return stat_interval_interval

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
