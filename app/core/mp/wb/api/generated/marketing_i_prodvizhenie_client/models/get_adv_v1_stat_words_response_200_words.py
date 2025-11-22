from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

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
    """Blok informatsii po kljuchevym frazam

    Attributes:
        phrase (Union[Unset, List[str]]): Frazovoe sootvetstvie (minus frazy)
        strong (Union[Unset, List[str]]): Tochnoe sootvetstvie (minus frazy)
        excluded (Union[Unset, List[str]]): Minus frazy iz poiska
        pluse (Union[Unset, List[str]]): Fiksirovannye frazy
        keywords (Union[Unset, List['GetAdvV1StatWordsResponse200WordsKeywordsItem']]): Blok so statistikoj po
            kljuchevym frazam
        fixed (Union[Unset, bool]): Fiksirovannye kljuchevye frazy (`true` — vkljucheny, `false` — vykljucheny)
    """

    phrase: Union[Unset, List[str]] = UNSET
    strong: Union[Unset, List[str]] = UNSET
    excluded: Union[Unset, List[str]] = UNSET
    pluse: Union[Unset, List[str]] = UNSET
    keywords: Union[Unset, List["GetAdvV1StatWordsResponse200WordsKeywordsItem"]] = UNSET
    fixed: Union[Unset, bool] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        phrase: Union[Unset, List[str]] = UNSET
        if not isinstance(self.phrase, Unset):
            phrase = self.phrase

        strong: Union[Unset, List[str]] = UNSET
        if not isinstance(self.strong, Unset):
            strong = self.strong

        excluded: Union[Unset, List[str]] = UNSET
        if not isinstance(self.excluded, Unset):
            excluded = self.excluded

        pluse: Union[Unset, List[str]] = UNSET
        if not isinstance(self.pluse, Unset):
            pluse = self.pluse

        keywords: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.keywords, Unset):
            keywords = []
            for keywords_item_data in self.keywords:
                keywords_item = keywords_item_data.to_dict()
                keywords.append(keywords_item)

        fixed = self.fixed

        field_dict: Dict[str, Any] = {}
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
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_adv_v1_stat_words_response_200_words_keywords_item import (
            GetAdvV1StatWordsResponse200WordsKeywordsItem,
        )

        d = src_dict.copy()
        phrase = cast(List[str], d.pop("phrase", UNSET))

        strong = cast(List[str], d.pop("strong", UNSET))

        excluded = cast(List[str], d.pop("excluded", UNSET))

        pluse = cast(List[str], d.pop("pluse", UNSET))

        keywords = []
        _keywords = d.pop("keywords", UNSET)
        for keywords_item_data in _keywords or []:
            keywords_item = GetAdvV1StatWordsResponse200WordsKeywordsItem.from_dict(keywords_item_data)

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
