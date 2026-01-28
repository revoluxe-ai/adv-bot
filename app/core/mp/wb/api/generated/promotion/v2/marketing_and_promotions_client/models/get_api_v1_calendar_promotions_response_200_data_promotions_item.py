from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.get_api_v1_calendar_promotions_response_200_data_promotions_item_type import (
    GetApiV1CalendarPromotionsResponse200DataPromotionsItemType,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="GetApiV1CalendarPromotionsResponse200DataPromotionsItem")


@_attrs_define
class GetApiV1CalendarPromotionsResponse200DataPromotionsItem:
    """
    Attributes:
        id (int | Unset): ID aktsii Example: 123.
        name (str | Unset): Nazvanie aktsii Example: skidki.
        start_date_time (datetime.datetime | Unset): Nachalo aktsii Example: 2023-06-05T21:00:00Z.
        end_date_time (datetime.datetime | Unset): Konets aktsii Example: 2023-06-05T21:00:00Z.
        type_ (GetApiV1CalendarPromotionsResponse200DataPromotionsItemType | Unset): Tip aktsii:
              - `regular` — aktsija
              - `auto` — avtoaktsija
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    start_date_time: datetime.datetime | Unset = UNSET
    end_date_time: datetime.datetime | Unset = UNSET
    type_: GetApiV1CalendarPromotionsResponse200DataPromotionsItemType | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        start_date_time: str | Unset = UNSET
        if not isinstance(self.start_date_time, Unset):
            start_date_time = self.start_date_time.isoformat()

        end_date_time: str | Unset = UNSET
        if not isinstance(self.end_date_time, Unset):
            end_date_time = self.end_date_time.isoformat()

        type_: str | Unset = UNSET
        if not isinstance(self.type_, Unset):
            type_ = self.type_.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if start_date_time is not UNSET:
            field_dict["startDateTime"] = start_date_time
        if end_date_time is not UNSET:
            field_dict["endDateTime"] = end_date_time
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        _start_date_time = d.pop("startDateTime", UNSET)
        start_date_time: datetime.datetime | Unset
        if isinstance(_start_date_time, Unset):
            start_date_time = UNSET
        else:
            start_date_time = isoparse(_start_date_time)

        _end_date_time = d.pop("endDateTime", UNSET)
        end_date_time: datetime.datetime | Unset
        if isinstance(_end_date_time, Unset):
            end_date_time = UNSET
        else:
            end_date_time = isoparse(_end_date_time)

        _type_ = d.pop("type", UNSET)
        type_: GetApiV1CalendarPromotionsResponse200DataPromotionsItemType | Unset
        if isinstance(_type_, Unset):
            type_ = UNSET
        else:
            type_ = GetApiV1CalendarPromotionsResponse200DataPromotionsItemType(_type_)

        get_api_v1_calendar_promotions_response_200_data_promotions_item = cls(
            id=id,
            name=name,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            type_=type_,
        )

        get_api_v1_calendar_promotions_response_200_data_promotions_item.additional_properties = d
        return get_api_v1_calendar_promotions_response_200_data_promotions_item

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
