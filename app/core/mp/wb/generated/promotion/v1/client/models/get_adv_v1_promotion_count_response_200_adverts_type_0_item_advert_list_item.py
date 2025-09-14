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

T = TypeVar(
    "T", bound="GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem"
)


@_attrs_define
class GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem:
    """
    Attributes:
        advert_id (Union[Unset, int]): ID kampanii
        change_time (Union[Unset, datetime.datetime]): Data i vremja poslednego izmenenija kampanii
    """

    advert_id: Union[Unset, int] = UNSET
    change_time: Union[Unset, datetime.datetime] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        change_time: Union[Unset, str] = UNSET
        if not isinstance(self.change_time, Unset):
            change_time = self.change_time.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if change_time is not UNSET:
            field_dict["changeTime"] = change_time

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        advert_id = d.pop("advertId", UNSET)

        _change_time = d.pop("changeTime", UNSET)
        change_time: Union[Unset, datetime.datetime]
        if isinstance(_change_time, Unset):
            change_time = UNSET
        else:
            change_time = isoparse(_change_time)

        get_adv_v1_promotion_count_response_200_adverts_type_0_item_advert_list_item = (
            cls(
                advert_id=advert_id,
                change_time=change_time,
            )
        )

        get_adv_v1_promotion_count_response_200_adverts_type_0_item_advert_list_item.additional_properties = d
        return (
            get_adv_v1_promotion_count_response_200_adverts_type_0_item_advert_list_item
        )

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
