from typing import Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.post_api_advert_v1_bids_min_body_payment_type import (
    PostApiAdvertV1BidsMinBodyPaymentType,
)
from ..models.post_api_advert_v1_bids_min_body_placement_types_item import (
    PostApiAdvertV1BidsMinBodyPlacementTypesItem,
)

T = TypeVar("T", bound="PostApiAdvertV1BidsMinBody")


@_attrs_define
class PostApiAdvertV1BidsMinBody:
    """
    Attributes:
        advert_id (int): Campaign ID
        nm_ids (List[int]): WB articles list
        payment_type (PostApiAdvertV1BidsMinBodyPaymentType): Payment type:
              - `cpm` — per mille
              - `cpc` — per click
        placement_types (List[PostApiAdvertV1BidsMinBodyPlacementTypesItem]): Placements:
              - `search` — search
              - `recommendation` — recommendation
              - `combined` — search and recommendation
    """

    advert_id: int
    nm_ids: List[int]
    payment_type: PostApiAdvertV1BidsMinBodyPaymentType
    placement_types: List[PostApiAdvertV1BidsMinBodyPlacementTypesItem]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nm_ids = self.nm_ids

        payment_type = self.payment_type.value

        placement_types = []
        for placement_types_item_data in self.placement_types:
            placement_types_item = placement_types_item_data.value
            placement_types.append(placement_types_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nm_ids": nm_ids,
                "payment_type": payment_type,
                "placement_types": placement_types,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        advert_id = d.pop("advert_id")

        nm_ids = cast(List[int], d.pop("nm_ids"))

        payment_type = PostApiAdvertV1BidsMinBodyPaymentType(d.pop("payment_type"))

        placement_types = []
        _placement_types = d.pop("placement_types")
        for placement_types_item_data in _placement_types:
            placement_types_item = PostApiAdvertV1BidsMinBodyPlacementTypesItem(
                placement_types_item_data
            )

            placement_types.append(placement_types_item)

        post_api_advert_v1_bids_min_body = cls(
            advert_id=advert_id,
            nm_ids=nm_ids,
            payment_type=payment_type,
            placement_types=placement_types,
        )

        post_api_advert_v1_bids_min_body.additional_properties = d
        return post_api_advert_v1_bids_min_body

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
