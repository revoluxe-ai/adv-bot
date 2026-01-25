from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v1_stat_words_response_200_words_keywords_item import (
        GetAdvV1StatWordsResponse200WordsKeywordsItem,
    )


T = TypeVar("T", bound="GetAdvV1StatWordsResponse200Words")


@_attrs_define
class GetAdvV1StatWordsResponse200Words:
    """Key phrase information block"

    Attributes:
        phrase (list[str] | Unset): Phrase matching (minus phrases)
        strong (list[str] | Unset): Exact match (minus phrases)
        excluded (list[str] | Unset): Minus phrases from search
        pluse (list[str] | Unset): Fixed phrases
        keywords (list[GetAdvV1StatWordsResponse200WordsKeywordsItem] | Unset): Dataset with statistics for key phrases
        fixed (bool | Unset): Fixed key phrases (`true` — enabled, `false` — disabled)
    """

    phrase: list[str] | Unset = UNSET
    strong: list[str] | Unset = UNSET
    excluded: list[str] | Unset = UNSET
    pluse: list[str] | Unset = UNSET
    keywords: list[GetAdvV1StatWordsResponse200WordsKeywordsItem] | Unset = UNSET
    fixed: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.get_adv_v1_stat_words_response_200_words_keywords_item import (
            GetAdvV1StatWordsResponse200WordsKeywordsItem,
        )

        phrase: list[str] | Unset = UNSET
        if not isinstance(self.phrase, Unset):
            phrase = self.phrase

        strong: list[str] | Unset = UNSET
        if not isinstance(self.strong, Unset):
            strong = self.strong

        excluded: list[str] | Unset = UNSET
        if not isinstance(self.excluded, Unset):
            excluded = self.excluded

        pluse: list[str] | Unset = UNSET
        if not isinstance(self.pluse, Unset):
            pluse = self.pluse

        keywords: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.keywords, Unset):
            keywords = []
            for keywords_item_data in self.keywords:
                keywords_item = keywords_item_data.to_dict()
                keywords.append(keywords_item)

        fixed = self.fixed

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if phrase is not UNSET:
            field_dict["phrase"] = phrase
        if strong is not UNSET:
            field_dict["strong"] = strong
        if excluded is not UNSET:
            field_dict["excluded"] = excluded
        if pluse is not UNSET:
            field_dict["pluse"] = pluse
        if keywords is not UNSET:
            field_dict["keywords"] = keywords
        if fixed is not UNSET:
            field_dict["fixed"] = fixed

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v1_stat_words_response_200_words_keywords_item import (
            GetAdvV1StatWordsResponse200WordsKeywordsItem,
        )

        d = dict(src_dict)
        phrase = cast(list[str], d.pop("phrase", UNSET))

        strong = cast(list[str], d.pop("strong", UNSET))

        excluded = cast(list[str], d.pop("excluded", UNSET))

        pluse = cast(list[str], d.pop("pluse", UNSET))

        _keywords = d.pop("keywords", UNSET)
        keywords: list[GetAdvV1StatWordsResponse200WordsKeywordsItem] | Unset = UNSET
        if _keywords is not UNSET:
            keywords = []
            for keywords_item_data in _keywords:
                keywords_item = GetAdvV1StatWordsResponse200WordsKeywordsItem.from_dict(
                    keywords_item_data
                )

                keywords.append(keywords_item)

        fixed = d.pop("fixed", UNSET)

        get_adv_v1_stat_words_response_200_words = cls(
            phrase=phrase,
            strong=strong,
            excluded=excluded,
            pluse=pluse,
            keywords=keywords,
            fixed=fixed,
        )

        get_adv_v1_stat_words_response_200_words.additional_properties = d
        return get_adv_v1_stat_words_response_200_words

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
