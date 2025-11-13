import datetime
from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1AdvertsResponse200Item")


@_attrs_define
class GetAdvV1AdvertsResponse200Item:
    """
    Attributes:
        advert_id (Union[Unset, int]): ID mediakampanii
        name (Union[Unset, str]): Nazvanie mediakampanii
        brand (Union[Unset, str]): Nazvanie brenda
        type (Union[Unset, int]): Tip mediakampanii:
            - `1` — razmeschenie po dnjam
            - `2` — razmeschenie po prosmotram
        status (Union[Unset, int]): Status mediakampanii:
              - `1` — chernovik
              - `2` — moderatsija
              - `3` — otklonena (s vozmozhnost'ju vernut' na moderatsiju)
              - `4` — gotova k zapusku
              - `5` — zaplanirovana
              - `6` — na pokazah
              - `7` — zavershena
              - `8` — otmenena
              - `9` — priostanovlena prodavtsom
              - `10` — pauza po dnevnomu limitu
              - `11` — pauza
        create_time (Union[Unset, datetime.datetime]): Vremja sozdanija mediakampanii
        end_time (Union[Unset, datetime.datetime]): Vremja zavershenija mediakampanii
    """

    advert_id: Union[Unset, int] = UNSET
    name: Union[Unset, str] = UNSET
    brand: Union[Unset, str] = UNSET
    type: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    create_time: Union[Unset, datetime.datetime] = UNSET
    end_time: Union[Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        name = self.name

        brand = self.brand

        type = self.type

        status = self.status

        create_time: Union[Unset, str] = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        end_time: Union[Unset, str] = UNSET
        if not isinstance(self.end_time, Unset):
            end_time = self.end_time.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if name is not UNSET:
            field_dict["name"] = name
        if brand is not UNSET:
            field_dict["brand"] = brand
        if type is not UNSET:
            field_dict["type"] = type
        if status is not UNSET:
            field_dict["status"] = status
        if create_time is not UNSET:
            field_dict["createTime"] = create_time
        if end_time is not UNSET:
            field_dict["endTime"] = end_time

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        advert_id = d.pop("advertId", UNSET)

        name = d.pop("name", UNSET)

        brand = d.pop("brand", UNSET)

        type = d.pop("type", UNSET)

        status = d.pop("status", UNSET)

        _create_time = d.pop("createTime", UNSET)
        create_time: Union[Unset, datetime.datetime]
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _end_time = d.pop("endTime", UNSET)
        end_time: Union[Unset, datetime.datetime]
        if isinstance(_end_time, Unset):
            end_time = UNSET
        else:
            end_time = isoparse(_end_time)

        get_adv_v1_adverts_response_200_item = cls(
            advert_id=advert_id,
            name=name,
            brand=brand,
            type=type,
            status=status,
            create_time=create_time,
            end_time=end_time,
        )

        get_adv_v1_adverts_response_200_item.additional_properties = d
        return get_adv_v1_adverts_response_200_item

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
