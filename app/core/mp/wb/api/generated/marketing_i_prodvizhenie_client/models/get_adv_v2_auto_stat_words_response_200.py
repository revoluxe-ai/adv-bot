from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

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
        excluded (Union[Unset, List[str]]): Iskljuchenija (minus-frazy) dlja tovarov iz kampanii. Mozhno zadat'
            pomosch'ju metoda [ustanovka/udalenie minus-fraz](./ru/openapi/promotion#tag/Parametry-
            kampanij/paths/~1adv~1v1~1search~1set-phrase/post) ili v nastrojkah kampanii v lichnom kabinete Example:
            ['Samsung', 'Xiaomi'].
        clusters (Union[Unset, List['GetAdvV2AutoStatWordsResponse200ClustersItem']]): Klastery kljuchevyh fraz
    """

    excluded: Union[Unset, List[str]] = UNSET
    clusters: Union[Unset, List["GetAdvV2AutoStatWordsResponse200ClustersItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        excluded: Union[Unset, List[str]] = UNSET
        if not isinstance(self.excluded, Unset):
            excluded = self.excluded

        clusters: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.clusters, Unset):
            clusters = []
            for clusters_item_data in self.clusters:
                clusters_item = clusters_item_data.to_dict()
                clusters.append(clusters_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if excluded is not UNSET:
            field_dict["excluded"] = excluded
        if clusters is not UNSET:
            field_dict["clusters"] = clusters

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_adv_v2_auto_stat_words_response_200_clusters_item import (
            GetAdvV2AutoStatWordsResponse200ClustersItem,
        )

        d = src_dict.copy()
        excluded = cast(List[str], d.pop("excluded", UNSET))

        clusters = []
        _clusters = d.pop("clusters", UNSET)
        for clusters_item_data in _clusters or []:
            clusters_item = GetAdvV2AutoStatWordsResponse200ClustersItem.from_dict(clusters_item_data)

            clusters.append(clusters_item)

        get_adv_v2_auto_stat_words_response_200 = cls(
            excluded=excluded,
            clusters=clusters,
        )

        get_adv_v2_auto_stat_words_response_200.additional_properties = d
        return get_adv_v2_auto_stat_words_response_200

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
