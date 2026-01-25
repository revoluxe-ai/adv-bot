from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1AdvertsResponse200Item")


@_attrs_define
class GetAdvV1AdvertsResponse200Item:
    """
    Attributes:
        advert_id (int | Unset): Media campaign ID
        name (str | Unset): Media campaign name
        brand (str | Unset): Brand name
        type_ (int | Unset): Media campaign type:
            - `1` — daily basis
            - `2` — views basis
        status (int | Unset): Media campaign status:
              - `1` — template
              - `2` — moderation
              - `3` — rejected (with the possibility to resubmit for moderation)
              - `4` — ready for launch
              - `5` — scheduled
              - `6` — running
              - `7` — completed
              - `8` — declined
              - `9` — paused by seller
              - `10` — paused due to daily limit
              - `11` — paused
        create_time (datetime.datetime | Unset): Time of media campaign creation
        end_time (datetime.datetime | Unset): Time of completion of the media campaign
    """

    advert_id: int | Unset = UNSET
    name: str | Unset = UNSET
    brand: str | Unset = UNSET
    type_: int | Unset = UNSET
    status: int | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    end_time: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        name = self.name

        brand = self.brand

        type_ = self.type_

        status = self.status

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        end_time: str | Unset = UNSET
        if not isinstance(self.end_time, Unset):
            end_time = self.end_time.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if name is not UNSET:
            field_dict["name"] = name
        if brand is not UNSET:
            field_dict["brand"] = brand
        if type_ is not UNSET:
            field_dict["type"] = type_
        if status is not UNSET:
            field_dict["status"] = status
        if create_time is not UNSET:
            field_dict["createTime"] = create_time
        if end_time is not UNSET:
            field_dict["endTime"] = end_time

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        advert_id = d.pop("advertId", UNSET)

        name = d.pop("name", UNSET)

        brand = d.pop("brand", UNSET)

        type_ = d.pop("type", UNSET)

        status = d.pop("status", UNSET)

        _create_time = d.pop("createTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _end_time = d.pop("endTime", UNSET)
        end_time: datetime.datetime | Unset
        if isinstance(_end_time, Unset):
            end_time = UNSET
        else:
            end_time = isoparse(_end_time)

        get_adv_v1_adverts_response_200_item = cls(
            advert_id=advert_id,
            name=name,
            brand=brand,
            type_=type_,
            status=status,
            create_time=create_time,
            end_time=end_time,
        )

        get_adv_v1_adverts_response_200_item.additional_properties = d
        return get_adv_v1_adverts_response_200_item

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
