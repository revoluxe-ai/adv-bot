from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="V0BidRecommendationBaseBidLeadersBid")


@_attrs_define
class V0BidRecommendationBaseBidLeadersBid:
    """Leaders bid — the average bid that allows products to occupy leading positions in your product category

    Attributes:
        bid_kopecks (Union[Unset, Any]): Recommended bid, kopecks
    """

    bid_kopecks: Union[Unset, Any] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        bid_kopecks = self.bid_kopecks

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if bid_kopecks is not UNSET:
            field_dict["bidKopecks"] = bid_kopecks

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        bid_kopecks = d.pop("bidKopecks", UNSET)

        v0_bid_recommendation_base_bid_leaders_bid = cls(
            bid_kopecks=bid_kopecks,
        )

        v0_bid_recommendation_base_bid_leaders_bid.additional_properties = d
        return v0_bid_recommendation_base_bid_leaders_bid

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
