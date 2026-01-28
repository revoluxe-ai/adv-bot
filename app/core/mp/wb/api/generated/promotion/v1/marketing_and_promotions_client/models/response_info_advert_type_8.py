from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.response_info_advert_type_8_auto_params import (
        ResponseInfoAdvertType8AutoParams,
    )


T = TypeVar("T", bound="ResponseInfoAdvertType8")


@_attrs_define
class ResponseInfoAdvertType8:
    """
    Attributes:
        end_time (datetime.datetime | Unset): Campaign end date
        create_time (datetime.datetime | Unset): Campaign create time
        change_time (datetime.datetime | Unset): Campaign last update time
        start_time (datetime.datetime | Unset): Campaign launch date
        auto_params (ResponseInfoAdvertType8AutoParams | Unset):
        name (str | Unset): Campaign name
        daily_budget (int | Unset): Not used
        advert_id (int | Unset): Campaign ID
        status (int | Unset): Campaign status:
            - `-1` — deleted, the deletion process will be completed within 10 minutes
            - `4` — ready to be launched
            - `7` — completed
            - `8` — declined
            - `9` — active
            - `11` — paused
        type_ (int | Unset): Type of campaign:
              - `8` — standard bid
        payment_type (str | Unset): Payment model:
            - `cpm` — per mille
    """

    end_time: datetime.datetime | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    change_time: datetime.datetime | Unset = UNSET
    start_time: datetime.datetime | Unset = UNSET
    auto_params: ResponseInfoAdvertType8AutoParams | Unset = UNSET
    name: str | Unset = UNSET
    daily_budget: int | Unset = UNSET
    advert_id: int | Unset = UNSET
    status: int | Unset = UNSET
    type_: int | Unset = UNSET
    payment_type: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.response_info_advert_type_8_auto_params import (
            ResponseInfoAdvertType8AutoParams,
        )

        end_time: str | Unset = UNSET
        if not isinstance(self.end_time, Unset):
            end_time = self.end_time.isoformat()

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        change_time: str | Unset = UNSET
        if not isinstance(self.change_time, Unset):
            change_time = self.change_time.isoformat()

        start_time: str | Unset = UNSET
        if not isinstance(self.start_time, Unset):
            start_time = self.start_time.isoformat()

        auto_params: dict[str, Any] | Unset = UNSET
        if not isinstance(self.auto_params, Unset):
            auto_params = self.auto_params.to_dict()

        name = self.name

        daily_budget = self.daily_budget

        advert_id = self.advert_id

        status = self.status

        type_ = self.type_

        payment_type = self.payment_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if end_time is not UNSET:
            field_dict["endTime"] = end_time
        if create_time is not UNSET:
            field_dict["createTime"] = create_time
        if change_time is not UNSET:
            field_dict["changeTime"] = change_time
        if start_time is not UNSET:
            field_dict["startTime"] = start_time
        if auto_params is not UNSET:
            field_dict["autoParams"] = auto_params
        if name is not UNSET:
            field_dict["name"] = name
        if daily_budget is not UNSET:
            field_dict["dailyBudget"] = daily_budget
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if status is not UNSET:
            field_dict["status"] = status
        if type_ is not UNSET:
            field_dict["type"] = type_
        if payment_type is not UNSET:
            field_dict["paymentType"] = payment_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.response_info_advert_type_8_auto_params import (
            ResponseInfoAdvertType8AutoParams,
        )

        d = dict(src_dict)
        _end_time = d.pop("endTime", UNSET)
        end_time: datetime.datetime | Unset
        if isinstance(_end_time, Unset):
            end_time = UNSET
        else:
            end_time = isoparse(_end_time)

        _create_time = d.pop("createTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _change_time = d.pop("changeTime", UNSET)
        change_time: datetime.datetime | Unset
        if isinstance(_change_time, Unset):
            change_time = UNSET
        else:
            change_time = isoparse(_change_time)

        _start_time = d.pop("startTime", UNSET)
        start_time: datetime.datetime | Unset
        if isinstance(_start_time, Unset):
            start_time = UNSET
        else:
            start_time = isoparse(_start_time)

        _auto_params = d.pop("autoParams", UNSET)
        auto_params: ResponseInfoAdvertType8AutoParams | Unset
        if isinstance(_auto_params, Unset):
            auto_params = UNSET
        else:
            auto_params = ResponseInfoAdvertType8AutoParams.from_dict(_auto_params)

        name = d.pop("name", UNSET)

        daily_budget = d.pop("dailyBudget", UNSET)

        advert_id = d.pop("advertId", UNSET)

        status = d.pop("status", UNSET)

        type_ = d.pop("type", UNSET)

        payment_type = d.pop("paymentType", UNSET)

        response_info_advert_type_8 = cls(
            end_time=end_time,
            create_time=create_time,
            change_time=change_time,
            start_time=start_time,
            auto_params=auto_params,
            name=name,
            daily_budget=daily_budget,
            advert_id=advert_id,
            status=status,
            type_=type_,
            payment_type=payment_type,
        )

        response_info_advert_type_8.additional_properties = d
        return response_info_advert_type_8

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
