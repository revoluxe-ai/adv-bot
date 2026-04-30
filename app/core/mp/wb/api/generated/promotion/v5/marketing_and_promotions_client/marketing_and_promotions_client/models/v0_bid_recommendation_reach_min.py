from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="V0BidRecommendationReachMin")


@_attrs_define
class V0BidRecommendationReachMin:
    """Minimum reach: 50-60%

    Attributes:
        bid_kopecks (Union[Unset, int]): Recommended bid, kopecks
        bid_kopecks_min (Union[Unset, int]): Minimum bid in kopecks
    """

    bid_kopecks: Union[Unset, int] = UNSET
    bid_kopecks_min: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        bid_kopecks = self.bid_kopecks

        bid_kopecks_min = self.bid_kopecks_min

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if bid_kopecks is not UNSET:
            field_dict["bidKopecks"] = bid_kopecks
        if bid_kopecks_min is not UNSET:
            field_dict["bidKopecksMin"] = bid_kopecks_min

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        bid_kopecks = d.pop("bidKopecks", UNSET)

        bid_kopecks_min = d.pop("bidKopecksMin", UNSET)

        v0_bid_recommendation_reach_min = cls(
            bid_kopecks=bid_kopecks,
            bid_kopecks_min=bid_kopecks_min,
        )

        v0_bid_recommendation_reach_min.additional_properties = d
        return v0_bid_recommendation_reach_min

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
