from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v1_advert_response_200_items_item_show_hours_item import (
        GetAdvV1AdvertResponse200ItemsItemShowHoursItem,
    )


T = TypeVar("T", bound="GetAdvV1AdvertResponse200ItemsItem")


@_attrs_define
class GetAdvV1AdvertResponse200ItemsItem:
    """
    Attributes:
        id (int | Unset): ID bannera
        name (str | Unset): Brend
        status (int | Unset): Status (takoj zhe kak u mediakampanii)
        place (int | Unset): Pozitsija na stranitse razmeschenija
        budget (int | Unset): Bjudzhet
        daily_limit (int | Unset): Dnevnoj limit (dlja bannerov po pokazam)
        category_name (str | Unset): Nazvanie kategorii razmeschenija
        cpm (int | Unset): Stavka
        url (str | Unset): URL stranitsy, na kotoruju popadaet pol'zovatel' pri klike po banneru
        advert_type (int | Unset): Tip prodvizhenija:
            - `1` — banner
            - `2` — vsplyvajuschee menju
            - `3` — pochtovaja rassylka
            - `4` — sotsial'nye seti
            - `5` — push-uvedomlenija v mobil'nom prilozhenii
        created_at (datetime.datetime | Unset): Data sozdanija bannera
        updated_at (datetime.datetime | Unset): Data i vremja obnovlenija bannera
        date_from (datetime.datetime | Unset): Data nachala raboty bannera
        date_to (datetime.datetime | Unset): Data zavershenija raboty bannera
        nms (list[int] | Unset): Podborka artikulov WB
        bottom_text_1 (str | Unset): Tekst pod plashkoj bannera
        bottom_text_2 (str | Unset): 2-ja stroka s tekstom pod plashkoj bannera
        message (str | Unset): Tekst push-uvedomlenija ili rassylki
        additional_settings (int | Unset): Dopolnitel'nye nastrojki.

            Format pochtovoj rassylki:
            - `1` — obschij
            - `2` — chastichnyj
            - `3` — unikal'nyj


            Sotsial'naja set':
            - `1` — VK
            - `2` — OK (Odnoklassniki)
        receivers_count (int | Unset): Kol-vo poluchatelej push-uvedomlenij
        subject_id (int | Unset): ID roditel'skoj kategorii tovara
        subject_name (str | Unset): Nazvanie roditel'skoj kategorii tovara
        action_name (str | Unset): Nazvanie aktsii
        show_hours (list[GetAdvV1AdvertResponse200ItemsItemShowHoursItem] | Unset): Chasy pokaza
        erid (str | Unset): Unikal'nyj ID mediakampanii dlja raboty s ORD
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    status: int | Unset = UNSET
    place: int | Unset = UNSET
    budget: int | Unset = UNSET
    daily_limit: int | Unset = UNSET
    category_name: str | Unset = UNSET
    cpm: int | Unset = UNSET
    url: str | Unset = UNSET
    advert_type: int | Unset = UNSET
    created_at: datetime.datetime | Unset = UNSET
    updated_at: datetime.datetime | Unset = UNSET
    date_from: datetime.datetime | Unset = UNSET
    date_to: datetime.datetime | Unset = UNSET
    nms: list[int] | Unset = UNSET
    bottom_text_1: str | Unset = UNSET
    bottom_text_2: str | Unset = UNSET
    message: str | Unset = UNSET
    additional_settings: int | Unset = UNSET
    receivers_count: int | Unset = UNSET
    subject_id: int | Unset = UNSET
    subject_name: str | Unset = UNSET
    action_name: str | Unset = UNSET
    show_hours: list[GetAdvV1AdvertResponse200ItemsItemShowHoursItem] | Unset = UNSET
    erid: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        status = self.status

        place = self.place

        budget = self.budget

        daily_limit = self.daily_limit

        category_name = self.category_name

        cpm = self.cpm

        url = self.url

        advert_type = self.advert_type

        created_at: str | Unset = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        updated_at: str | Unset = UNSET
        if not isinstance(self.updated_at, Unset):
            updated_at = self.updated_at.isoformat()

        date_from: str | Unset = UNSET
        if not isinstance(self.date_from, Unset):
            date_from = self.date_from.isoformat()

        date_to: str | Unset = UNSET
        if not isinstance(self.date_to, Unset):
            date_to = self.date_to.isoformat()

        nms: list[int] | Unset = UNSET
        if not isinstance(self.nms, Unset):
            nms = self.nms

        bottom_text_1 = self.bottom_text_1

        bottom_text_2 = self.bottom_text_2

        message = self.message

        additional_settings = self.additional_settings

        receivers_count = self.receivers_count

        subject_id = self.subject_id

        subject_name = self.subject_name

        action_name = self.action_name

        show_hours: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.show_hours, Unset):
            show_hours = []
            for show_hours_item_data in self.show_hours:
                show_hours_item = show_hours_item_data.to_dict()
                show_hours.append(show_hours_item)

        erid = self.erid

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if status is not UNSET:
            field_dict["status"] = status
        if place is not UNSET:
            field_dict["place"] = place
        if budget is not UNSET:
            field_dict["budget"] = budget
        if daily_limit is not UNSET:
            field_dict["daily_limit"] = daily_limit
        if category_name is not UNSET:
            field_dict["category_name"] = category_name
        if cpm is not UNSET:
            field_dict["cpm"] = cpm
        if url is not UNSET:
            field_dict["url"] = url
        if advert_type is not UNSET:
            field_dict["advert_type"] = advert_type
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if date_from is not UNSET:
            field_dict["date_from"] = date_from
        if date_to is not UNSET:
            field_dict["date_to"] = date_to
        if nms is not UNSET:
            field_dict["nms"] = nms
        if bottom_text_1 is not UNSET:
            field_dict["bottomText1"] = bottom_text_1
        if bottom_text_2 is not UNSET:
            field_dict["bottomText2"] = bottom_text_2
        if message is not UNSET:
            field_dict["message"] = message
        if additional_settings is not UNSET:
            field_dict["additionalSettings"] = additional_settings
        if receivers_count is not UNSET:
            field_dict["receiversCount"] = receivers_count
        if subject_id is not UNSET:
            field_dict["subject_id"] = subject_id
        if subject_name is not UNSET:
            field_dict["subject_name"] = subject_name
        if action_name is not UNSET:
            field_dict["action_name"] = action_name
        if show_hours is not UNSET:
            field_dict["show_hours"] = show_hours
        if erid is not UNSET:
            field_dict["Erid"] = erid

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v1_advert_response_200_items_item_show_hours_item import (
            GetAdvV1AdvertResponse200ItemsItemShowHoursItem,
        )

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        status = d.pop("status", UNSET)

        place = d.pop("place", UNSET)

        budget = d.pop("budget", UNSET)

        daily_limit = d.pop("daily_limit", UNSET)

        category_name = d.pop("category_name", UNSET)

        cpm = d.pop("cpm", UNSET)

        url = d.pop("url", UNSET)

        advert_type = d.pop("advert_type", UNSET)

        _created_at = d.pop("created_at", UNSET)
        created_at: datetime.datetime | Unset
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        _updated_at = d.pop("updated_at", UNSET)
        updated_at: datetime.datetime | Unset
        if isinstance(_updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = isoparse(_updated_at)

        _date_from = d.pop("date_from", UNSET)
        date_from: datetime.datetime | Unset
        if isinstance(_date_from, Unset):
            date_from = UNSET
        else:
            date_from = isoparse(_date_from)

        _date_to = d.pop("date_to", UNSET)
        date_to: datetime.datetime | Unset
        if isinstance(_date_to, Unset):
            date_to = UNSET
        else:
            date_to = isoparse(_date_to)

        nms = cast(list[int], d.pop("nms", UNSET))

        bottom_text_1 = d.pop("bottomText1", UNSET)

        bottom_text_2 = d.pop("bottomText2", UNSET)

        message = d.pop("message", UNSET)

        additional_settings = d.pop("additionalSettings", UNSET)

        receivers_count = d.pop("receiversCount", UNSET)

        subject_id = d.pop("subject_id", UNSET)

        subject_name = d.pop("subject_name", UNSET)

        action_name = d.pop("action_name", UNSET)

        _show_hours = d.pop("show_hours", UNSET)
        show_hours: list[GetAdvV1AdvertResponse200ItemsItemShowHoursItem] | Unset = (
            UNSET
        )
        if _show_hours is not UNSET:
            show_hours = []
            for show_hours_item_data in _show_hours:
                show_hours_item = (
                    GetAdvV1AdvertResponse200ItemsItemShowHoursItem.from_dict(
                        show_hours_item_data
                    )
                )

                show_hours.append(show_hours_item)

        erid = d.pop("Erid", UNSET)

        get_adv_v1_advert_response_200_items_item = cls(
            id=id,
            name=name,
            status=status,
            place=place,
            budget=budget,
            daily_limit=daily_limit,
            category_name=category_name,
            cpm=cpm,
            url=url,
            advert_type=advert_type,
            created_at=created_at,
            updated_at=updated_at,
            date_from=date_from,
            date_to=date_to,
            nms=nms,
            bottom_text_1=bottom_text_1,
            bottom_text_2=bottom_text_2,
            message=message,
            additional_settings=additional_settings,
            receivers_count=receivers_count,
            subject_id=subject_id,
            subject_name=subject_name,
            action_name=action_name,
            show_hours=show_hours,
            erid=erid,
        )

        get_adv_v1_advert_response_200_items_item.additional_properties = d
        return get_adv_v1_advert_response_200_items_item

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
