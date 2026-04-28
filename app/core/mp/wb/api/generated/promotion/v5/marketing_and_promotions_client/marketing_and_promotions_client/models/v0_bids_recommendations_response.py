from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_bid_recommendation_base import V0BidRecommendationBase
    from ..models.v0_bid_recommendation_norm_query import V0BidRecommendationNormQuery


T = TypeVar("T", bound="V0BidsRecommendationsResponse")


@_attrs_define
class V0BidsRecommendationsResponse:
    """
    Attributes:
        advert_id (Union[Unset, int]): Campaign ID
        base (Union[Unset, V0BidRecommendationBase]): Recommended bids for items
        nm_id (Union[Unset, int]): WB article ID
        norm_queries (Union[Unset, List['V0BidRecommendationNormQuery']]): Recommended bids for search clusters
    """

    advert_id: Union[Unset, int] = UNSET
    base: Union[Unset, "V0BidRecommendationBase"] = UNSET
    nm_id: Union[Unset, int] = UNSET
    norm_queries: Union[Unset, List["V0BidRecommendationNormQuery"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        base: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.base, Unset):
            base = self.base.to_dict()

        nm_id = self.nm_id

        norm_queries: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.norm_queries, Unset):
            norm_queries = []
            for norm_queries_item_data in self.norm_queries:
                norm_queries_item = norm_queries_item_data.to_dict()
                norm_queries.append(norm_queries_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if base is not UNSET:
            field_dict["base"] = base
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if norm_queries is not UNSET:
            field_dict["normQueries"] = norm_queries

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_bid_recommendation_base import V0BidRecommendationBase
        from ..models.v0_bid_recommendation_norm_query import (
            V0BidRecommendationNormQuery,
        )

        d = src_dict.copy()
        advert_id = d.pop("advertId", UNSET)

        _base = d.pop("base", UNSET)
        base: Union[Unset, V0BidRecommendationBase]
        if isinstance(_base, Unset):
            base = UNSET
        else:
            base = V0BidRecommendationBase.from_dict(_base)

        nm_id = d.pop("nmId", UNSET)

        norm_queries = []
        _norm_queries = d.pop("normQueries", UNSET)
        for norm_queries_item_data in _norm_queries or []:
            norm_queries_item = V0BidRecommendationNormQuery.from_dict(
                norm_queries_item_data
            )

            norm_queries.append(norm_queries_item)

        v0_bids_recommendations_response = cls(
            advert_id=advert_id,
            base=base,
            nm_id=nm_id,
            norm_queries=norm_queries,
        )

        v0_bids_recommendations_response.additional_properties = d
        return v0_bids_recommendations_response

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
