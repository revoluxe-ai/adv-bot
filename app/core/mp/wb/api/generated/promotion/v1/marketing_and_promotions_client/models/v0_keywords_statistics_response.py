from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_keywords_statistics import V0KeywordsStatistics


T = TypeVar("T", bound="V0KeywordsStatisticsResponse")


@_attrs_define
class V0KeywordsStatisticsResponse:
    """
    Attributes:
        keywords (list[V0KeywordsStatistics]):
    """

    keywords: list[V0KeywordsStatistics]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.v0_keywords_statistics import V0KeywordsStatistics

        keywords = []
        for keywords_item_data in self.keywords:
            keywords_item = keywords_item_data.to_dict()
            keywords.append(keywords_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "keywords": keywords,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.v0_keywords_statistics import V0KeywordsStatistics

        d = dict(src_dict)
        keywords = []
        _keywords = d.pop("keywords")
        for keywords_item_data in _keywords:
            keywords_item = V0KeywordsStatistics.from_dict(keywords_item_data)

            keywords.append(keywords_item)

        v0_keywords_statistics_response = cls(
            keywords=keywords,
        )

        v0_keywords_statistics_response.additional_properties = d
        return v0_keywords_statistics_response

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
