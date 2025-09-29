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
    from ..models.get_adv_v1_advert_response_200_extended import (
        GetAdvV1AdvertResponse200Extended,
    )
    from ..models.get_adv_v1_advert_response_200_items_item import (
        GetAdvV1AdvertResponse200ItemsItem,
    )


T = TypeVar("T", bound="GetAdvV1AdvertResponse200")


@_attrs_define
class GetAdvV1AdvertResponse200:
    """
    Example:
        {'advertId': 23569, 'name': 'Reklama deneg prinesi', 'brand': 'Plank', 'type': 2, 'status': 11, 'createTime':
            '2023-07-19T11:13:41.195138+03:00', 'extended': {'reason': 'Dlja vozobnovlenija pokazov popolnite bjudzhet
            mediakampanii', 'expenses': 10000, 'from': '2023-07-19T12:05:35.847348Z', 'to':
            '2123-07-20T08:14:13.079176+03:00', 'updated_at': '2023-07-21T13:25:31.129766+03:00', 'price': 0, 'budget': 0,
            'operation': 1, 'contract_id': 0}, 'items': [{'id': 68080, 'name': 'Unison', 'status': 7, 'place': 2, 'budget':
            650000, 'daily_limit': 500, 'category_name': 'Glavnaja', 'cpm': 351, 'url':
            'https://www.wildberries.ru/promotions/ssylka-na-akciyou', 'advert_type': 1, 'created_at':
            '2023-11-01T15:40:46.86165+03:00', 'updated_at': '2023-11-08T23:44:33.248229+03:00', 'date_from':
            '2023-11-01T16:05:22.286002Z', 'date_to': '2023-11-09T17:27:32.745869+03:00', 'nms': [123456, 11111111],
            'bottomText1': 'string', 'bottomText2': 'string', 'message': 'string', 'additionalSettings': 1,
            'receiversCount': 1, 'subject_id': 6945, 'subject_name': "Bel'e", 'action_name': 'Rasprodazha! Sozdaj sebe
            domashnij ujut!', 'show_hours': [{'From': 7, 'To': 8}], 'Erid': 'string'}]}

    Attributes:
        advert_id (Union[Unset, int]): ID mediakampanii
        name (Union[Unset, str]): Nazvanie mediakampanii
        brand (Union[Unset, str]): Nazvanie brenda
        type_ (Union[Unset, int]): <dl>
            <dt>Tip mediakampanii:</dt>
            <dd><code>1</code> — razmeschenie po dnjam</dd>
            <dd><code>2</code> — razmeschenie po prosmotram</dd>
            </dl>
        status (Union[Unset, int]): <dl>
            <dt>Status mediakampanii:</dt>
              <dd><code>1</code> — chernovik</dd>
              <dd><code>2</code> — moderatsija
              <dd><code>3</code> — otklonena (s vozmozhnost'ju vernut' na moderatsiju)</dd>
              <dd><code>4</code> — gotova k zapusku</dd>
              <dd><code>5</code> — zaplanirovana</dd>
              <dd><code>6</code> — na pokazah</dd>
              <dd><code>7</code> — zavershena</dd>
              <dd><code>8</code> — otmenena</dd>
              <dd><code>9</code> — priostanovlena prodavtsom</dd>
              <dd><code>10</code> — pauza po dnevnomu limitu</dd>
              <dd><code>11</code> — pauza</dd>
            </dl>
        create_time (Union[Unset, datetime.datetime]): Vremja sozdanija mediakampanii
        extended (Union[Unset, GetAdvV1AdvertResponse200Extended]):
        items (Union[Unset, list['GetAdvV1AdvertResponse200ItemsItem']]): Informatsija o bannere.
            <br>
            Nalichie v otvete teh ili inyh polej zavisit ot konfiguratsii mediakampanii.
    """

    advert_id: Union[Unset, int] = UNSET
    name: Union[Unset, str] = UNSET
    brand: Union[Unset, str] = UNSET
    type_: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    create_time: Union[Unset, datetime.datetime] = UNSET
    extended: Union[Unset, "GetAdvV1AdvertResponse200Extended"] = UNSET
    items: Union[Unset, list["GetAdvV1AdvertResponse200ItemsItem"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        name = self.name

        brand = self.brand

        type_ = self.type_

        status = self.status

        create_time: Union[Unset, str] = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        extended: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.extended, Unset):
            extended = self.extended.to_dict()

        items: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.items, Unset):
            items = []
            for items_item_data in self.items:
                items_item = items_item_data.to_dict()
                items.append(items_item)

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
        if extended is not UNSET:
            field_dict["extended"] = extended
        if items is not UNSET:
            field_dict["items"] = items

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v1_advert_response_200_extended import (
            GetAdvV1AdvertResponse200Extended,
        )
        from ..models.get_adv_v1_advert_response_200_items_item import (
            GetAdvV1AdvertResponse200ItemsItem,
        )

        d = dict(src_dict)
        advert_id = d.pop("advertId", UNSET)

        name = d.pop("name", UNSET)

        brand = d.pop("brand", UNSET)

        type_ = d.pop("type", UNSET)

        status = d.pop("status", UNSET)

        _create_time = d.pop("createTime", UNSET)
        create_time: Union[Unset, datetime.datetime]
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _extended = d.pop("extended", UNSET)
        extended: Union[Unset, GetAdvV1AdvertResponse200Extended]
        if isinstance(_extended, Unset):
            extended = UNSET
        else:
            extended = GetAdvV1AdvertResponse200Extended.from_dict(_extended)

        items = []
        _items = d.pop("items", UNSET)
        for items_item_data in _items or []:
            items_item = GetAdvV1AdvertResponse200ItemsItem.from_dict(items_item_data)

            items.append(items_item)

        get_adv_v1_advert_response_200 = cls(
            advert_id=advert_id,
            name=name,
            brand=brand,
            type_=type_,
            status=status,
            create_time=create_time,
            extended=extended,
            items=items,
        )

        get_adv_v1_advert_response_200.additional_properties = d
        return get_adv_v1_advert_response_200

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
