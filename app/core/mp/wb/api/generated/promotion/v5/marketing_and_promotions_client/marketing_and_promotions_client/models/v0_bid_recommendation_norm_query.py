from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_bid_recommendation_reach_max import V0BidRecommendationReachMax
    from ..models.v0_bid_recommendation_reach_medium import (
        V0BidRecommendationReachMedium,
    )
    from ..models.v0_bid_recommendation_reach_min import V0BidRecommendationReachMin


T = TypeVar("T", bound="V0BidRecommendationNormQuery")


@_attrs_define
class V0BidRecommendationNormQuery:
    """
    Attributes:
        norm_query (Union[Unset, str]): Search cluster
        reach_max (Union[Unset, V0BidRecommendationReachMax]): Max reach: 76–100%
        reach_medium (Union[Unset, V0BidRecommendationReachMedium]): Medium reach: 61-75% coverage
        reach_min (Union[Unset, V0BidRecommendationReachMin]): Minimum reach: 50-60%
    """

    norm_query: Union[Unset, str] = UNSET
    reach_max: Union[Unset, "V0BidRecommendationReachMax"] = UNSET
    reach_medium: Union[Unset, "V0BidRecommendationReachMedium"] = UNSET
    reach_min: Union[Unset, "V0BidRecommendationReachMin"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        norm_query = self.norm_query

        reach_max: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.reach_max, Unset):
            reach_max = self.reach_max.to_dict()

        reach_medium: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.reach_medium, Unset):
            reach_medium = self.reach_medium.to_dict()

        reach_min: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.reach_min, Unset):
            reach_min = self.reach_min.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if norm_query is not UNSET:
            field_dict["normQuery"] = norm_query
        if reach_max is not UNSET:
            field_dict["reachMax"] = reach_max
        if reach_medium is not UNSET:
            field_dict["reachMedium"] = reach_medium
        if reach_min is not UNSET:
            field_dict["reachMin"] = reach_min

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_bid_recommendation_reach_max import V0BidRecommendationReachMax
        from ..models.v0_bid_recommendation_reach_medium import (
            V0BidRecommendationReachMedium,
        )
        from ..models.v0_bid_recommendation_reach_min import V0BidRecommendationReachMin

        d = src_dict.copy()
        norm_query = d.pop("normQuery", UNSET)

        _reach_max = d.pop("reachMax", UNSET)
        reach_max: Union[Unset, V0BidRecommendationReachMax]
        if isinstance(_reach_max, Unset):
            reach_max = UNSET
        else:
            reach_max = V0BidRecommendationReachMax.from_dict(_reach_max)

        _reach_medium = d.pop("reachMedium", UNSET)
        reach_medium: Union[Unset, V0BidRecommendationReachMedium]
        if isinstance(_reach_medium, Unset):
            reach_medium = UNSET
        else:
            reach_medium = V0BidRecommendationReachMedium.from_dict(_reach_medium)

        _reach_min = d.pop("reachMin", UNSET)
        reach_min: Union[Unset, V0BidRecommendationReachMin]
        if isinstance(_reach_min, Unset):
            reach_min = UNSET
        else:
            reach_min = V0BidRecommendationReachMin.from_dict(_reach_min)

        v0_bid_recommendation_norm_query = cls(
            norm_query=norm_query,
            reach_max=reach_max,
            reach_medium=reach_medium,
            reach_min=reach_min,
        )

        v0_bid_recommendation_norm_query.additional_properties = d
        return v0_bid_recommendation_norm_query

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
