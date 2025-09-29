from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_api_v1_calendar_promotions_response_200_data_promotions_item_type import (
    GetApiV1CalendarPromotionsResponse200DataPromotionsItemType,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="GetApiV1CalendarPromotionsResponse200DataPromotionsItem")


@_attrs_define
class GetApiV1CalendarPromotionsResponse200DataPromotionsItem:
    """
    Attributes:
        id (Union[Unset, int]): ID aktsii Example: 123.
        name (Union[Unset, str]): Nazvanie aktsii Example: skidki.
        start_date_time (Union[Unset, str]): Nachalo aktsii Example: 2023-06-05T21:00:00Z.
        end_date_time (Union[Unset, str]): Konets aktsii Example: 2023-06-05T21:00:00Z.
        type_ (Union[Unset, GetApiV1CalendarPromotionsResponse200DataPromotionsItemType]): Tip aktsii:
              - `regular` — aktsija
              - `auto` — avtoaktsija
    """

    id: Union[Unset, int] = UNSET
    name: Union[Unset, str] = UNSET
    start_date_time: Union[Unset, str] = UNSET
    end_date_time: Union[Unset, str] = UNSET
    type_: Union[Unset, GetApiV1CalendarPromotionsResponse200DataPromotionsItemType] = (
        UNSET
    )
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        start_date_time = self.start_date_time

        end_date_time = self.end_date_time

        type_: Union[Unset, str] = UNSET
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

        start_date_time = d.pop("startDateTime", UNSET)

        end_date_time = d.pop("endDateTime", UNSET)

        _type_ = d.pop("type", UNSET)
        type_: Union[Unset, GetApiV1CalendarPromotionsResponse200DataPromotionsItemType]
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

        get_api_v1_calendar_promotions_response_200_data_promotions_item.additional_properties = (
            d
        )
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
