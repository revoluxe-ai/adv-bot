from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="AdvertBidsKopecks")


@_attrs_define
class AdvertBidsKopecks:
    """Stavki, kopejki

    Attributes:
        search (int): Stavka v poiske
        recommendations (int): Stavka v rekomendatsijah
    """

    search: int
    recommendations: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        search = self.search

        recommendations = self.recommendations

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "search": search,
                "recommendations": recommendations,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any] | None) -> T:
        d = dict(src_dict or {})
        search = d.pop("search", 0)
        if search is None:
            search = 0

        recommendations = d.pop("recommendations", 0)
        if recommendations is None:
            recommendations = 0

        advert_bids_kopecks = cls(
            search=search,
            recommendations=recommendations,
        )

        advert_bids_kopecks.additional_properties = d
        return advert_bids_kopecks

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
