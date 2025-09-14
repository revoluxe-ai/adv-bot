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

T = TypeVar("T", bound="GetAdvV1StatWordsResponse200StatItem")


@_attrs_define
class GetAdvV1StatWordsResponse200StatItem:
    """
    Attributes:
        advert_id (Union[Unset, int]): ID kampanii v sisteme WB
        keyword (Union[Unset, str]): Kljuchevaja fraza
        advert_name (Union[Unset, str]): Pole permanentno otkljucheno
        campaign_name (Union[Unset, str]): Nazvanie kampanii
        begin (Union[Unset, datetime.datetime]): Data zapuska kampanii
        end (Union[Unset, datetime.datetime]): Data zavershenija kampanii
        views (Union[Unset, int]): Kolichestvo prosmotrov
        clicks (Union[Unset, int]): Kolichestvo klikov
        frq (Union[Unset, int]): Chastota (otnoshenie kolichestva prosmotrov k kolichestvu unikal'nyh pol'zovatelej)
        ctr (Union[Unset, float]): Pokazatel' klikabel'nosti (otnoshenie chisla klikov k kolichestvu pokazov.
            Vyrazhaetsja v protsentah).
        cpc (Union[Unset, float]): Stoimost' klika, ₽
        duration (Union[Unset, int]): Dlitel'nost' kampanii, v sekundah
        sum_ (Union[Unset, float]): Zatraty, ₽.
    """

    advert_id: Union[Unset, int] = UNSET
    keyword: Union[Unset, str] = UNSET
    advert_name: Union[Unset, str] = UNSET
    campaign_name: Union[Unset, str] = UNSET
    begin: Union[Unset, datetime.datetime] = UNSET
    end: Union[Unset, datetime.datetime] = UNSET
    views: Union[Unset, int] = UNSET
    clicks: Union[Unset, int] = UNSET
    frq: Union[Unset, int] = UNSET
    ctr: Union[Unset, float] = UNSET
    cpc: Union[Unset, float] = UNSET
    duration: Union[Unset, int] = UNSET
    sum_: Union[Unset, float] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        keyword = self.keyword

        advert_name = self.advert_name

        campaign_name = self.campaign_name

        begin: Union[Unset, str] = UNSET
        if not isinstance(self.begin, Unset):
            begin = self.begin.isoformat()

        end: Union[Unset, str] = UNSET
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
        begin: Union[Unset, datetime.datetime]
        if isinstance(_begin, Unset):
            begin = UNSET
        else:
            begin = isoparse(_begin)

        _end = d.pop("end", UNSET)
        end: Union[Unset, datetime.datetime]
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
