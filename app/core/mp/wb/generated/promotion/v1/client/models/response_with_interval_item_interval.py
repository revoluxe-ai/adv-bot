import datetime
from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponseWithIntervalItemInterval")


@_attrs_define
class ResponseWithIntervalItemInterval:
    """Period

    Attributes:
        begin (Union[Unset, datetime.date]): Nachalo perioda
        end (Union[Unset, datetime.date]): Konets perioda
    """

    begin: Union[Unset, datetime.date] = UNSET
    end: Union[Unset, datetime.date] = UNSET

    def to_dict(self) -> dict[str, Any]:
        begin: Union[Unset, str] = UNSET
        if not isinstance(self.begin, Unset):
            begin = self.begin.isoformat()

        end: Union[Unset, str] = UNSET
        if not isinstance(self.end, Unset):
            end = self.end.isoformat()

        field_dict: dict[str, Any] = {}

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

        response_with_interval_item_interval = cls(
            begin=begin,
            end=end,
        )

        return response_with_interval_item_interval
