from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_get_norm_query_list_response_item_norm_queries import (
        V0GetNormQueryListResponseItemNormQueries,
    )


T = TypeVar("T", bound="V0GetNormQueryListResponseItem")


@_attrs_define
class V0GetNormQueryListResponseItem:
    """
    Attributes:
        advert_id (Union[Unset, int]): Campaign ID
        nm_id (Union[Unset, int]): WB article
        norm_queries (Union[Unset, V0GetNormQueryListResponseItemNormQueries]): Search clusters
    """

    advert_id: Union[Unset, int] = UNSET
    nm_id: Union[Unset, int] = UNSET
    norm_queries: Union[Unset, "V0GetNormQueryListResponseItemNormQueries"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        norm_queries: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.norm_queries, Unset):
            norm_queries = self.norm_queries.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if norm_queries is not UNSET:
            field_dict["normQueries"] = norm_queries

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_get_norm_query_list_response_item_norm_queries import (
            V0GetNormQueryListResponseItemNormQueries,
        )

        d = src_dict.copy()
        advert_id = d.pop("advertId", UNSET)

        nm_id = d.pop("nmId", UNSET)

        _norm_queries = d.pop("normQueries", UNSET)
        norm_queries: Union[Unset, V0GetNormQueryListResponseItemNormQueries]
        if isinstance(_norm_queries, Unset):
            norm_queries = UNSET
        else:
            norm_queries = V0GetNormQueryListResponseItemNormQueries.from_dict(
                _norm_queries
            )

        v0_get_norm_query_list_response_item = cls(
            advert_id=advert_id,
            nm_id=nm_id,
            norm_queries=norm_queries,
        )

        v0_get_norm_query_list_response_item.additional_properties = d
        return v0_get_norm_query_list_response_item

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
