from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.post_adv_v2_seacat_save_ad_body_bid_type import (
    PostAdvV2SeacatSaveAdBodyBidType,
)
from ..models.post_adv_v2_seacat_save_ad_body_payment_type import (
    PostAdvV2SeacatSaveAdBodyPaymentType,
)
from ..models.post_adv_v2_seacat_save_ad_body_placement_types_item import (
    PostAdvV2SeacatSaveAdBodyPlacementTypesItem,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV2SeacatSaveAdBody")


@_attrs_define
class PostAdvV2SeacatSaveAdBody:
    """
    Attributes:
        name (Union[Unset, str]): Campaign name
        nms (Union[Unset, List[int]]): Product card for this campaign. You can available product cards with [product
            cards for campaigns](./promotion#tag/Campaigns-Creation/paths/~1adv~1v2~1supplier~1nms/post) method. Maximum of
            50 products (`nm`)
        bid_type (Union[Unset, PostAdvV2SeacatSaveAdBodyBidType]): Тип ставки:
              - `manual` — ручная
              - `unified` — единая
             Default: PostAdvV2SeacatSaveAdBodyBidType.MANUAL.
        payment_type (Union[Unset, PostAdvV2SeacatSaveAdBodyPaymentType]): Payment type:
            - `cpm` — cost per mille
            - `cpc` — cost per click. When creating a campaign with this payment type, a minimum bid is automatically set
             Default: PostAdvV2SeacatSaveAdBodyPaymentType.CPM.
        placement_types (Union[Unset, List[PostAdvV2SeacatSaveAdBodyPlacementTypesItem]]): Placements:
              - `search` — search
              - `recommendations` — recommendations

             Specify for campaign with custom bid only
    """

    name: Union[Unset, str] = UNSET
    nms: Union[Unset, List[int]] = UNSET
    bid_type: Union[
        Unset, PostAdvV2SeacatSaveAdBodyBidType
    ] = PostAdvV2SeacatSaveAdBodyBidType.MANUAL
    payment_type: Union[
        Unset, PostAdvV2SeacatSaveAdBodyPaymentType
    ] = PostAdvV2SeacatSaveAdBodyPaymentType.CPM
    placement_types: Union[
        Unset, List[PostAdvV2SeacatSaveAdBodyPlacementTypesItem]
    ] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        nms: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nms, Unset):
            nms = self.nms

        bid_type: Union[Unset, str] = UNSET
        if not isinstance(self.bid_type, Unset):
            bid_type = self.bid_type.value

        payment_type: Union[Unset, str] = UNSET
        if not isinstance(self.payment_type, Unset):
            payment_type = self.payment_type.value

        placement_types: Union[Unset, List[str]] = UNSET
        if not isinstance(self.placement_types, Unset):
            placement_types = []
            for placement_types_item_data in self.placement_types:
                placement_types_item = placement_types_item_data.value
                placement_types.append(placement_types_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if nms is not UNSET:
            field_dict["nms"] = nms
        if bid_type is not UNSET:
            field_dict["bid_type"] = bid_type
        if payment_type is not UNSET:
            field_dict["payment_type"] = payment_type
        if placement_types is not UNSET:
            field_dict["placement_types"] = placement_types

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name", UNSET)

        nms = cast(List[int], d.pop("nms", UNSET))

        _bid_type = d.pop("bid_type", UNSET)
        bid_type: Union[Unset, PostAdvV2SeacatSaveAdBodyBidType]
        if isinstance(_bid_type, Unset):
            bid_type = UNSET
        else:
            bid_type = PostAdvV2SeacatSaveAdBodyBidType(_bid_type)

        _payment_type = d.pop("payment_type", UNSET)
        payment_type: Union[Unset, PostAdvV2SeacatSaveAdBodyPaymentType]
        if isinstance(_payment_type, Unset):
            payment_type = UNSET
        else:
            payment_type = PostAdvV2SeacatSaveAdBodyPaymentType(_payment_type)

        placement_types = []
        _placement_types = d.pop("placement_types", UNSET)
        for placement_types_item_data in _placement_types or []:
            placement_types_item = PostAdvV2SeacatSaveAdBodyPlacementTypesItem(
                placement_types_item_data
            )

            placement_types.append(placement_types_item)

        post_adv_v2_seacat_save_ad_body = cls(
            name=name,
            nms=nms,
            bid_type=bid_type,
            payment_type=payment_type,
            placement_types=placement_types,
        )

        post_adv_v2_seacat_save_ad_body.additional_properties = d
        return post_adv_v2_seacat_save_ad_body

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
