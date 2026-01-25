from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v1_stat_words_response_200_stat_item import (
        GetAdvV1StatWordsResponse200StatItem,
    )
    from ..models.get_adv_v1_stat_words_response_200_words import (
        GetAdvV1StatWordsResponse200Words,
    )


T = TypeVar("T", bound="GetAdvV1StatWordsResponse200")


@_attrs_define
class GetAdvV1StatWordsResponse200:
    """
    Attributes:
        words (GetAdvV1StatWordsResponse200Words | Unset): Blok informatsii po kljuchevym frazam
        stat (list[GetAdvV1StatWordsResponse200StatItem] | Unset): Massiv informatsii po statistike.<br>
            **Pervyj element massiva** s `keyword: "Vsego po kampanii"` soderzhit summarnuju informatsiju obo vseh
            kljuchevyh frazah.<br>
            **Kazhdyj sledujuschij element massiva** soderzhit informatsiju ob otdel'nyh kljuchevyh frazah.<br>
            Otobrazhaetsja 60 kljuchevyh fraz s naibol'shim kolichestvom prosmotrov.
    """

    words: GetAdvV1StatWordsResponse200Words | Unset = UNSET
    stat: list[GetAdvV1StatWordsResponse200StatItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        words: dict[str, Any] | Unset = UNSET
        if not isinstance(self.words, Unset):
            words = self.words.to_dict()

        stat: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.stat, Unset):
            stat = []
            for stat_item_data in self.stat:
                stat_item = stat_item_data.to_dict()
                stat.append(stat_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if words is not UNSET:
            field_dict["words"] = words
        if stat is not UNSET:
            field_dict["stat"] = stat

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v1_stat_words_response_200_stat_item import (
            GetAdvV1StatWordsResponse200StatItem,
        )
        from ..models.get_adv_v1_stat_words_response_200_words import (
            GetAdvV1StatWordsResponse200Words,
        )

        d = dict(src_dict)
        _words = d.pop("words", UNSET)
        words: GetAdvV1StatWordsResponse200Words | Unset
        if isinstance(_words, Unset):
            words = UNSET
        else:
            words = GetAdvV1StatWordsResponse200Words.from_dict(_words)

        _stat = d.pop("stat", UNSET)
        stat: list[GetAdvV1StatWordsResponse200StatItem] | Unset = UNSET
        if _stat is not UNSET:
            stat = []
            for stat_item_data in _stat:
                stat_item = GetAdvV1StatWordsResponse200StatItem.from_dict(
                    stat_item_data
                )

                stat.append(stat_item)

        get_adv_v1_stat_words_response_200 = cls(
            words=words,
            stat=stat,
        )

        get_adv_v1_stat_words_response_200.additional_properties = d
        return get_adv_v1_stat_words_response_200

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
