from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1StatWordsResponse200WordsKeywordsItem")


@_attrs_define
class GetAdvV1StatWordsResponse200WordsKeywordsItem:
    """
    Attributes:
        keyword (str | Unset): Kljuchevaja fraza
        count (int | Unset): Kolichestvo prosmotrov po kljuchevoj fraze
    """

    keyword: str | Unset = UNSET
    count: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        keyword = self.keyword

        count = self.count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if keyword is not UNSET:
            field_dict["keyword"] = keyword
        if count is not UNSET:
            field_dict["count"] = count

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        keyword = d.pop("keyword", UNSET)

        count = d.pop("count", UNSET)

        get_adv_v1_stat_words_response_200_words_keywords_item = cls(
            keyword=keyword,
            count=count,
        )

        get_adv_v1_stat_words_response_200_words_keywords_item.additional_properties = d
        return get_adv_v1_stat_words_response_200_words_keywords_item

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
