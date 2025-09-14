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
    from ..models.response_info_advert_type_8_auto_params import (
        ResponseInfoAdvertType8AutoParams,
    )


T = TypeVar("T", bound="ResponseInfoAdvertType8")


@_attrs_define
class ResponseInfoAdvertType8:
    """
    Attributes:
        end_time (Union[Unset, datetime.datetime]): Data zavershenija kampanii
        create_time (Union[Unset, datetime.datetime]): Data sozdanija kampanii
        change_time (Union[Unset, datetime.datetime]): Data poslednego izmenenija kampanii
        start_time (Union[Unset, datetime.datetime]): Data poslednego zapuska kampanii
        auto_params (Union[Unset, ResponseInfoAdvertType8AutoParams]):
        name (Union[Unset, str]): Nazvanie kampanii
        daily_budget (Union[Unset, int]): Ne ispol'zuetsja
        advert_id (Union[Unset, int]): ID kampanii
        status (Union[Unset, int]): <dl>
            <dt>Status kampanii:</dt>
            <dd><code>-1</code> — udalena, protsess udalenija budet zavershen v techenie 10 minut</dd>
            <dd><code>4</code> — gotova k zapusku </dd>
            <dd><code>7</code> — zavershena</dd>
            <dd><code>8</code> — otmenena</dd>
            <dd><code>9</code> — aktivna</dd>
            <dd><code>11</code> — na pauze</dd>
            </dl>
        type_ (Union[Unset, int]): <dl>
            <dt>Tip kampanii:</dt>
              <dd><code>8</code> — edinaja stavka</dd>
            </dl>
        payment_type (Union[Unset, str]): Model' oplaty:
            - `cpm` — za pokazy
    """

    end_time: Union[Unset, datetime.datetime] = UNSET
    create_time: Union[Unset, datetime.datetime] = UNSET
    change_time: Union[Unset, datetime.datetime] = UNSET
    start_time: Union[Unset, datetime.datetime] = UNSET
    auto_params: Union[Unset, "ResponseInfoAdvertType8AutoParams"] = UNSET
    name: Union[Unset, str] = UNSET
    daily_budget: Union[Unset, int] = UNSET
    advert_id: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    type_: Union[Unset, int] = UNSET
    payment_type: Union[Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        end_time: Union[Unset, str] = UNSET
        if not isinstance(self.end_time, Unset):
            end_time = self.end_time.isoformat()

        create_time: Union[Unset, str] = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        change_time: Union[Unset, str] = UNSET
        if not isinstance(self.change_time, Unset):
            change_time = self.change_time.isoformat()

        start_time: Union[Unset, str] = UNSET
        if not isinstance(self.start_time, Unset):
            start_time = self.start_time.isoformat()

        auto_params: Union[Unset, dict[str, Any]] = UNSET
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
        end_time: Union[Unset, datetime.datetime]
        if isinstance(_end_time, Unset):
            end_time = UNSET
        else:
            end_time = isoparse(_end_time)

        _create_time = d.pop("createTime", UNSET)
        create_time: Union[Unset, datetime.datetime]
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _change_time = d.pop("changeTime", UNSET)
        change_time: Union[Unset, datetime.datetime]
        if isinstance(_change_time, Unset):
            change_time = UNSET
        else:
            change_time = isoparse(_change_time)

        _start_time = d.pop("startTime", UNSET)
        start_time: Union[Unset, datetime.datetime]
        if isinstance(_start_time, Unset):
            start_time = UNSET
        else:
            start_time = isoparse(_start_time)

        _auto_params = d.pop("autoParams", UNSET)
        auto_params: Union[Unset, ResponseInfoAdvertType8AutoParams]
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
