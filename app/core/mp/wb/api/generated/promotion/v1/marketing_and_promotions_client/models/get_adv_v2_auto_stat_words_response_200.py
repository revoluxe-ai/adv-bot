from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v2_auto_stat_words_response_200_clusters_item import (
        GetAdvV2AutoStatWordsResponse200ClustersItem,
    )


T = TypeVar("T", bound="GetAdvV2AutoStatWordsResponse200")


@_attrs_define
class GetAdvV2AutoStatWordsResponse200:
    """
    Attributes:
        excluded (list[str] | Unset): Exclusions (negative phrases) for products from the campaign. These are phrases
            that you set using the "Set/Delete Negative Phrases" method or in the personal account, in the campaign
            settings. Example: ['Samsung', 'Xiaomi'].
        clusters (list[GetAdvV2AutoStatWordsResponse200ClustersItem] | Unset): Key phrases clusters
    """

    excluded: list[str] | Unset = UNSET
    clusters: list[GetAdvV2AutoStatWordsResponse200ClustersItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.get_adv_v2_auto_stat_words_response_200_clusters_item import (
            GetAdvV2AutoStatWordsResponse200ClustersItem,
        )

        excluded: list[str] | Unset = UNSET
        if not isinstance(self.excluded, Unset):
            excluded = self.excluded

        clusters: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.clusters, Unset):
            clusters = []
            for clusters_item_data in self.clusters:
                clusters_item = clusters_item_data.to_dict()
                clusters.append(clusters_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if excluded is not UNSET:
            field_dict["excluded"] = excluded
        if clusters is not UNSET:
            field_dict["clusters"] = clusters

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v2_auto_stat_words_response_200_clusters_item import (
            GetAdvV2AutoStatWordsResponse200ClustersItem,
        )

        d = dict(src_dict)
        excluded = cast(list[str], d.pop("excluded", UNSET))

        _clusters = d.pop("clusters", UNSET)
        clusters: list[GetAdvV2AutoStatWordsResponse200ClustersItem] | Unset = UNSET
        if _clusters is not UNSET:
            clusters = []
            for clusters_item_data in _clusters:
                clusters_item = GetAdvV2AutoStatWordsResponse200ClustersItem.from_dict(
                    clusters_item_data
                )

                clusters.append(clusters_item)

        get_adv_v2_auto_stat_words_response_200 = cls(
            excluded=excluded,
            clusters=clusters,
        )

        get_adv_v2_auto_stat_words_response_200.additional_properties = d
        return get_adv_v2_auto_stat_words_response_200

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
