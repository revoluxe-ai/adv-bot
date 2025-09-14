from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1UpdResponse200Item")


@_attrs_define
class GetAdvV1UpdResponse200Item:
    """
    Attributes:
        upd_num (Union[Unset, int]): Nomer vystavlennogo dokumenta
        upd_time (Union[None, Unset, str]): Vremja spisanija
        upd_sum (Union[Unset, int]): Vystavlennaja summa
        advert_id (Union[Unset, int]): ID kampanii
        camp_name (Union[Unset, str]): Nazvanie kampanii
        advert_type (Union[Unset, int]): Tip kampanii
        payment_type (Union[Unset, str]): Istochnik spisanija:
             - `Balans`
             - `Bonusy`
             - `Schet`
             - `Keshbek`
        advert_status (Union[Unset, int]): <dl>
            <dt>Status kampanii:</dt>
            <dd><code>-1</code> — udalena, protsess udalenija budet zavershen v techenie 10 minut</dd>
            <dd><code>4</code> — gotova k zapusku </dd>
            <dd><code>7</code> — zavershena</dd>
            <dd><code>8</code> — otmenena</dd>
            <dd><code>9</code> — aktivna</dd>
            <dd><code>11</code> — na pauze</dd>
            </dl>
    """

    upd_num: Union[Unset, int] = UNSET
    upd_time: Union[None, Unset, str] = UNSET
    upd_sum: Union[Unset, int] = UNSET
    advert_id: Union[Unset, int] = UNSET
    camp_name: Union[Unset, str] = UNSET
    advert_type: Union[Unset, int] = UNSET
    payment_type: Union[Unset, str] = UNSET
    advert_status: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        upd_num = self.upd_num

        upd_time: Union[None, Unset, str]
        if isinstance(self.upd_time, Unset):
            upd_time = UNSET
        else:
            upd_time = self.upd_time

        upd_sum = self.upd_sum

        advert_id = self.advert_id

        camp_name = self.camp_name

        advert_type = self.advert_type

        payment_type = self.payment_type

        advert_status = self.advert_status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if upd_num is not UNSET:
            field_dict["updNum"] = upd_num
        if upd_time is not UNSET:
            field_dict["updTime"] = upd_time
        if upd_sum is not UNSET:
            field_dict["updSum"] = upd_sum
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if camp_name is not UNSET:
            field_dict["campName"] = camp_name
        if advert_type is not UNSET:
            field_dict["advertType"] = advert_type
        if payment_type is not UNSET:
            field_dict["paymentType"] = payment_type
        if advert_status is not UNSET:
            field_dict["advertStatus"] = advert_status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        upd_num = d.pop("updNum", UNSET)

        def _parse_upd_time(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        upd_time = _parse_upd_time(d.pop("updTime", UNSET))

        upd_sum = d.pop("updSum", UNSET)

        advert_id = d.pop("advertId", UNSET)

        camp_name = d.pop("campName", UNSET)

        advert_type = d.pop("advertType", UNSET)

        payment_type = d.pop("paymentType", UNSET)

        advert_status = d.pop("advertStatus", UNSET)

        get_adv_v1_upd_response_200_item = cls(
            upd_num=upd_num,
            upd_time=upd_time,
            upd_sum=upd_sum,
            advert_id=advert_id,
            camp_name=camp_name,
            advert_type=advert_type,
            payment_type=payment_type,
            advert_status=advert_status,
        )

        get_adv_v1_upd_response_200_item.additional_properties = d
        return get_adv_v1_upd_response_200_item

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
