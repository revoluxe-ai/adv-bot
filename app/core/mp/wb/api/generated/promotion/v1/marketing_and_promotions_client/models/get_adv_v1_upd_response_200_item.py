from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1UpdResponse200Item")


@_attrs_define
class GetAdvV1UpdResponse200Item:
    """
    Attributes:
        upd_num (int | Unset): Billing document number (if any)
        upd_time (None | str | Unset): Time of charge-off
        upd_sum (int | Unset): Amount invoiced
        advert_id (int | Unset): Campaign ID
        camp_name (str | Unset): Campaign name
        advert_type (int | Unset): Campaign type
        payment_type (str | Unset): Source of charge-off:
             - `Balans` — Balance
             - `Bonusy` — Bonuses
             - `Schet` — Money account
             - `Keshbek` — Debit card cashback
        advert_status (int | Unset): Campaign status:
            - `-1` — deleted, the deletion process will be completed within 10 minutes
            - `4` — ready to be launched
            - `7` — completed
            - `8` — declined
            - `9` — active
            - `11` — paused
    """

    upd_num: int | Unset = UNSET
    upd_time: None | str | Unset = UNSET
    upd_sum: int | Unset = UNSET
    advert_id: int | Unset = UNSET
    camp_name: str | Unset = UNSET
    advert_type: int | Unset = UNSET
    payment_type: str | Unset = UNSET
    advert_status: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        upd_num = self.upd_num

        upd_time: None | str | Unset
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

        def _parse_upd_time(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

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
