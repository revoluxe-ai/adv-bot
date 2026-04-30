from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_bid_recommendation_base_bid_competitive_bid import (
        V0BidRecommendationBaseBidCompetitiveBid,
    )
    from ..models.v0_bid_recommendation_base_bid_leaders_bid import (
        V0BidRecommendationBaseBidLeadersBid,
    )
    from ..models.v0_bid_recommendation_base_bid_top_2 import (
        V0BidRecommendationBaseBidTop2,
    )


T = TypeVar("T", bound="V0BidRecommendationBase")


@_attrs_define
class V0BidRecommendationBase:
    """Recommended bids for items

    Attributes:
        competitive_bid (Union[Unset, V0BidRecommendationBaseBidCompetitiveBid]): Competitive bid — the estimated
            average bid of other sellers who are selling similar products at a similar price level.
            Half of the sellers included in the calculation have a bid higher than the competitive rate, and the other half
            have a bid lower than it.
        leaders_bid (Union[Unset, V0BidRecommendationBaseBidLeadersBid]): Leaders bid — the average bid that allows
            products to occupy leading positions in your product category
        top2 (Union[Unset, V0BidRecommendationBaseBidTop2]): Top bid
    """

    competitive_bid: Union[Unset, "V0BidRecommendationBaseBidCompetitiveBid"] = UNSET
    leaders_bid: Union[Unset, "V0BidRecommendationBaseBidLeadersBid"] = UNSET
    top2: Union[Unset, "V0BidRecommendationBaseBidTop2"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        competitive_bid: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.competitive_bid, Unset):
            competitive_bid = self.competitive_bid.to_dict()

        leaders_bid: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.leaders_bid, Unset):
            leaders_bid = self.leaders_bid.to_dict()

        top2: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.top2, Unset):
            top2 = self.top2.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if competitive_bid is not UNSET:
            field_dict["competitiveBid"] = competitive_bid
        if leaders_bid is not UNSET:
            field_dict["leadersBid"] = leaders_bid
        if top2 is not UNSET:
            field_dict["top2"] = top2

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_bid_recommendation_base_bid_competitive_bid import (
            V0BidRecommendationBaseBidCompetitiveBid,
        )
        from ..models.v0_bid_recommendation_base_bid_leaders_bid import (
            V0BidRecommendationBaseBidLeadersBid,
        )
        from ..models.v0_bid_recommendation_base_bid_top_2 import (
            V0BidRecommendationBaseBidTop2,
        )

        d = src_dict.copy()
        _competitive_bid = d.pop("competitiveBid", UNSET)
        competitive_bid: Union[Unset, V0BidRecommendationBaseBidCompetitiveBid]
        if isinstance(_competitive_bid, Unset):
            competitive_bid = UNSET
        else:
            competitive_bid = V0BidRecommendationBaseBidCompetitiveBid.from_dict(
                _competitive_bid
            )

        _leaders_bid = d.pop("leadersBid", UNSET)
        leaders_bid: Union[Unset, V0BidRecommendationBaseBidLeadersBid]
        if isinstance(_leaders_bid, Unset):
            leaders_bid = UNSET
        else:
            leaders_bid = V0BidRecommendationBaseBidLeadersBid.from_dict(_leaders_bid)

        _top2 = d.pop("top2", UNSET)
        top2: Union[Unset, V0BidRecommendationBaseBidTop2]
        if isinstance(_top2, Unset):
            top2 = UNSET
        else:
            top2 = V0BidRecommendationBaseBidTop2.from_dict(_top2)

        v0_bid_recommendation_base = cls(
            competitive_bid=competitive_bid,
            leaders_bid=leaders_bid,
            top2=top2,
        )

        v0_bid_recommendation_base.additional_properties = d
        return v0_bid_recommendation_base

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
