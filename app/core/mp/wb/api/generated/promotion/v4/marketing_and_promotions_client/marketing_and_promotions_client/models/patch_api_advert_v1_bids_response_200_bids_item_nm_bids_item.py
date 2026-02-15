from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PatchApiAdvertV1BidsResponse200BidsItemNmBidsItem")


@_attrs_define
class PatchApiAdvertV1BidsResponse200BidsItemNmBidsItem:
    """
    Attributes:
        nm_id (int): WB article
        bid_kopecks (int): Bid
        placement (str): Placement:
              - `search` — in search
              - `recommendations`— in recommendations
    """

    nm_id: int
    bid_kopecks: int
    placement: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        bid_kopecks = self.bid_kopecks

        placement = self.placement

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nm_id": nm_id,
                "bid_kopecks": bid_kopecks,
                "placement": placement,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        nm_id = d.pop("nm_id")

        bid_kopecks = d.pop("bid_kopecks")

        placement = d.pop("placement")

        patch_api_advert_v1_bids_response_200_bids_item_nm_bids_item = cls(
            nm_id=nm_id,
            bid_kopecks=bid_kopecks,
            placement=placement,
        )

        patch_api_advert_v1_bids_response_200_bids_item_nm_bids_item.additional_properties = d
        return patch_api_advert_v1_bids_response_200_bids_item_nm_bids_item

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
