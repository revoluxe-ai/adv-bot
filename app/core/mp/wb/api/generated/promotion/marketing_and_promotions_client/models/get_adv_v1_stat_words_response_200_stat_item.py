from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1StatWordsResponse200StatItem")


@_attrs_define
class GetAdvV1StatWordsResponse200StatItem:
    """
    Attributes:
        advert_id (int | Unset): Campaign ID in the WB system
        keyword (str | Unset): Key phrase
        advert_name (str | Unset): Field permanently disabled
        campaign_name (str | Unset): Name of campaign
        begin (datetime.datetime | Unset): Campaign launch date
        end (datetime.datetime | Unset): Campaign end date
        views (int | Unset): Number of views
        clicks (int | Unset): Number of clicks
        frq (int | Unset): Frequency — ratio of the number of views to the number of unique users
        ctr (float | Unset): Slick-through rate — the ratio of clicks to displays, %
        cpc (float | Unset): Cost per click, ₽
        duration (int | Unset): Duration of the campaign, in seconds
        sum_ (float | Unset): Expenses, ₽
    """

    advert_id: int | Unset = UNSET
    keyword: str | Unset = UNSET
    advert_name: str | Unset = UNSET
    campaign_name: str | Unset = UNSET
    begin: datetime.datetime | Unset = UNSET
    end: datetime.datetime | Unset = UNSET
    views: int | Unset = UNSET
    clicks: int | Unset = UNSET
    frq: int | Unset = UNSET
    ctr: float | Unset = UNSET
    cpc: float | Unset = UNSET
    duration: int | Unset = UNSET
    sum_: float | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        keyword = self.keyword

        advert_name = self.advert_name

        campaign_name = self.campaign_name

        begin: str | Unset = UNSET
        if not isinstance(self.begin, Unset):
            begin = self.begin.isoformat()

        end: str | Unset = UNSET
        if not isinstance(self.end, Unset):
            end = self.end.isoformat()

        views = self.views

        clicks = self.clicks

        frq = self.frq

        ctr = self.ctr

        cpc = self.cpc

        duration = self.duration

        sum_ = self.sum_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if keyword is not UNSET:
            field_dict["keyword"] = keyword
        if advert_name is not UNSET:
            field_dict["advertName"] = advert_name
        if campaign_name is not UNSET:
            field_dict["campaignName"] = campaign_name
        if begin is not UNSET:
            field_dict["begin"] = begin
        if end is not UNSET:
            field_dict["end"] = end
        if views is not UNSET:
            field_dict["views"] = views
        if clicks is not UNSET:
            field_dict["clicks"] = clicks
        if frq is not UNSET:
            field_dict["frq"] = frq
        if ctr is not UNSET:
            field_dict["ctr"] = ctr
        if cpc is not UNSET:
            field_dict["cpc"] = cpc
        if duration is not UNSET:
            field_dict["duration"] = duration
        if sum_ is not UNSET:
            field_dict["sum"] = sum_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        advert_id = d.pop("advertId", UNSET)

        keyword = d.pop("keyword", UNSET)

        advert_name = d.pop("advertName", UNSET)

        campaign_name = d.pop("campaignName", UNSET)

        _begin = d.pop("begin", UNSET)
        begin: datetime.datetime | Unset
        if isinstance(_begin, Unset):
            begin = UNSET
        else:
            begin = isoparse(_begin)

        _end = d.pop("end", UNSET)
        end: datetime.datetime | Unset
        if isinstance(_end, Unset):
            end = UNSET
        else:
            end = isoparse(_end)

        views = d.pop("views", UNSET)

        clicks = d.pop("clicks", UNSET)

        frq = d.pop("frq", UNSET)

        ctr = d.pop("ctr", UNSET)

        cpc = d.pop("cpc", UNSET)

        duration = d.pop("duration", UNSET)

        sum_ = d.pop("sum", UNSET)

        get_adv_v1_stat_words_response_200_stat_item = cls(
            advert_id=advert_id,
            keyword=keyword,
            advert_name=advert_name,
            campaign_name=campaign_name,
            begin=begin,
            end=end,
            views=views,
            clicks=clicks,
            frq=frq,
            ctr=ctr,
            cpc=cpc,
            duration=duration,
            sum_=sum_,
        )

        get_adv_v1_stat_words_response_200_stat_item.additional_properties = d
        return get_adv_v1_stat_words_response_200_stat_item

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
