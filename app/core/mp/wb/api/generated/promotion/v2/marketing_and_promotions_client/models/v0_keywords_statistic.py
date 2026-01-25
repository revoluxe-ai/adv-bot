from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="V0KeywordsStatistic")


@_attrs_define
class V0KeywordsStatistic:
    """
    Attributes:
        clicks (int): Kolichestvo klikov
        ctr (float): CTR (Click-Through Rate) — pokazatel' klikabel'nosti
        keyword (str): Kljuchevaja fraza
        sum_ (float): Summa zatrat po kljuchevoj fraze
        views (int): Kolichestvo pokazov
    """

    clicks: int
    ctr: float
    keyword: str
    sum_: float
    views: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        clicks = self.clicks

        ctr = self.ctr

        keyword = self.keyword

        sum_ = self.sum_

        views = self.views

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "clicks": clicks,
                "ctr": ctr,
                "keyword": keyword,
                "sum": sum_,
                "views": views,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        clicks = d.pop("clicks")

        ctr = d.pop("ctr")

        keyword = d.pop("keyword")

        sum_ = d.pop("sum")

        views = d.pop("views")

        v0_keywords_statistic = cls(
            clicks=clicks,
            ctr=ctr,
            keyword=keyword,
            sum_=sum_,
            views=views,
        )

        v0_keywords_statistic.additional_properties = d
        return v0_keywords_statistic

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
