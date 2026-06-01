from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.placement_type import PlacementType

T = TypeVar("T", bound="PostApiAdvertV1BidsMinResponse200BidsItemBidsItem")


@_attrs_define
class PostApiAdvertV1BidsMinResponse200BidsItemBidsItem:
    """
    Attributes:
        type (PlacementType): Placements:
              - `search` — search
              - `recommendation` — recommendation
              - `combined` — search and recommendation
        value (int): Minimum bid, kopecks
    """

    type: PlacementType
    value: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        type = self.type.value

        value = self.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        type = PlacementType(d.pop("type"))

        value = d.pop("value")

        post_api_advert_v1_bids_min_response_200_bids_item_bids_item = cls(
            type=type,
            value=value,
        )

        post_api_advert_v1_bids_min_response_200_bids_item_bids_item.additional_properties = d
        return post_api_advert_v1_bids_min_response_200_bids_item_bids_item

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
