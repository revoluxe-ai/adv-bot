from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

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
        name (str | Unset): Nazvanie kampanii
        nms (list[int] | Unset): Kartochki tovarov dlja kampanii. Dostupnye kartochki tovarov mozhno poluchit' s
            pomosch'ju metoda [Kartochki tovarov dlja kampanij](./promotion#tag/Sozdanie-
            kampanij/paths/~1adv~1v2~1supplier~1nms/post). Maksimum 50 tovarov (`nm`)
        bid_type (PostAdvV2SeacatSaveAdBodyBidType | Unset): Tip stavki:
              - `manual` — ruchnaja
              - `unified` — edinaja
             Default: PostAdvV2SeacatSaveAdBodyBidType.MANUAL.
        payment_type (PostAdvV2SeacatSaveAdBodyPaymentType | Unset): Tip oplaty:
            - `cpm` — za pokazy
            - `cpc` — za klik. Pri sozdanii s etim tipom oplaty v kampanii avtomaticheski ustanavlivaetsja minimal'naja
            stavka
             Default: PostAdvV2SeacatSaveAdBodyPaymentType.CPM.
        placement_types (list[PostAdvV2SeacatSaveAdBodyPlacementTypesItem] | Unset): Mesta razmeschenija:
              - `search` — v poiske
              - `recommendations` — v rekomendatsijah

            Ukazhite tol'ko dlja kampanii s ruchnoj stavkoj
    """

    name: str | Unset = UNSET
    nms: list[int] | Unset = UNSET
    bid_type: PostAdvV2SeacatSaveAdBodyBidType | Unset = (
        PostAdvV2SeacatSaveAdBodyBidType.MANUAL
    )
    payment_type: PostAdvV2SeacatSaveAdBodyPaymentType | Unset = (
        PostAdvV2SeacatSaveAdBodyPaymentType.CPM
    )
    placement_types: list[PostAdvV2SeacatSaveAdBodyPlacementTypesItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        nms: list[int] | Unset = UNSET
        if not isinstance(self.nms, Unset):
            nms = self.nms

        bid_type: str | Unset = UNSET
        if not isinstance(self.bid_type, Unset):
            bid_type = self.bid_type.value

        payment_type: str | Unset = UNSET
        if not isinstance(self.payment_type, Unset):
            payment_type = self.payment_type.value

        placement_types: list[str] | Unset = UNSET
        if not isinstance(self.placement_types, Unset):
            placement_types = []
            for placement_types_item_data in self.placement_types:
                placement_types_item = placement_types_item_data.value
                placement_types.append(placement_types_item)

        field_dict: dict[str, Any] = {}
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
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name", UNSET)

        nms = cast(list[int], d.pop("nms", UNSET))

        _bid_type = d.pop("bid_type", UNSET)
        bid_type: PostAdvV2SeacatSaveAdBodyBidType | Unset
        if isinstance(_bid_type, Unset):
            bid_type = UNSET
        else:
            bid_type = PostAdvV2SeacatSaveAdBodyBidType(_bid_type)

        _payment_type = d.pop("payment_type", UNSET)
        payment_type: PostAdvV2SeacatSaveAdBodyPaymentType | Unset
        if isinstance(_payment_type, Unset):
            payment_type = UNSET
        else:
            payment_type = PostAdvV2SeacatSaveAdBodyPaymentType(_payment_type)

        _placement_types = d.pop("placement_types", UNSET)
        placement_types: list[PostAdvV2SeacatSaveAdBodyPlacementTypesItem] | Unset = (
            UNSET
        )
        if _placement_types is not UNSET:
            placement_types = []
            for placement_types_item_data in _placement_types:
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
