from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.post_adv_v0_bids_min_body_payment_type import (
    PostAdvV0BidsMinBodyPaymentType,
)
from ..models.post_adv_v0_bids_min_body_placement_types_item import (
    PostAdvV0BidsMinBodyPlacementTypesItem,
)

T = TypeVar("T", bound="PostAdvV0BidsMinBody")


@_attrs_define
class PostAdvV0BidsMinBody:
    """
    Attributes:
        advert_id (int): ID kampanii
        nm_ids (list[int]): Spisok artikulov WB
        payment_type (PostAdvV0BidsMinBodyPaymentType): Tip oplaty:
                  - `cpm` — za pokazy
                  - `cpc` — za klik
        placement_types (list[PostAdvV0BidsMinBodyPlacementTypesItem]): Zony pokazov:
              - `search` — poisk
              - `recommendation` — rekomendatsii
              - `combined` — poisk i rekomendatsii
    """

    advert_id: int
    nm_ids: list[int]
    payment_type: PostAdvV0BidsMinBodyPaymentType
    placement_types: list[PostAdvV0BidsMinBodyPlacementTypesItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        nm_ids = self.nm_ids

        payment_type = self.payment_type.value

        placement_types = []
        for placement_types_item_data in self.placement_types:
            placement_types_item = placement_types_item_data.value
            placement_types.append(placement_types_item)

        field_dict: dict[str, Any] = {}
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
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        advert_id = d.pop("advert_id")

        nm_ids = cast(list[int], d.pop("nm_ids"))

        payment_type = PostAdvV0BidsMinBodyPaymentType(d.pop("payment_type"))

        placement_types = []
        _placement_types = d.pop("placement_types")
        for placement_types_item_data in _placement_types:
            placement_types_item = PostAdvV0BidsMinBodyPlacementTypesItem(
                placement_types_item_data
            )

            placement_types.append(placement_types_item)

        post_adv_v0_bids_min_body = cls(
            advert_id=advert_id,
            nm_ids=nm_ids,
            payment_type=payment_type,
            placement_types=placement_types,
        )

        post_adv_v0_bids_min_body.additional_properties = d
        return post_adv_v0_bids_min_body

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
