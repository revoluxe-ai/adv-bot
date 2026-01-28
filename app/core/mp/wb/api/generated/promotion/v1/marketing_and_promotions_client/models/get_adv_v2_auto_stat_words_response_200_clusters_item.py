from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV2AutoStatWordsResponse200ClustersItem")


@_attrs_define
class GetAdvV2AutoStatWordsResponse200ClustersItem:
    """
    Attributes:
        cluster (str | Unset): Cluster — a set of similar key phrases Example: Phone.
        count (int | Unset): The number of times products were shown for all phrases in the cluster Example: 100.
        keywords (list[str] | Unset): Key phrases from the cluster for which products were shown at least once Example:
            ['Telefon', "Mobil'nyj telefon"].
    """

    cluster: str | Unset = UNSET
    count: int | Unset = UNSET
    keywords: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cluster = self.cluster

        count = self.count

        keywords: list[str] | Unset = UNSET
        if not isinstance(self.keywords, Unset):
            keywords = self.keywords

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cluster is not UNSET:
            field_dict["cluster"] = cluster
        if count is not UNSET:
            field_dict["count"] = count
        if keywords is not UNSET:
            field_dict["keywords"] = keywords

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        cluster = d.pop("cluster", UNSET)

        count = d.pop("count", UNSET)

        keywords = cast(list[str], d.pop("keywords", UNSET))

        get_adv_v2_auto_stat_words_response_200_clusters_item = cls(
            cluster=cluster,
            count=count,
            keywords=keywords,
        )

        get_adv_v2_auto_stat_words_response_200_clusters_item.additional_properties = d
        return get_adv_v2_auto_stat_words_response_200_clusters_item

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
