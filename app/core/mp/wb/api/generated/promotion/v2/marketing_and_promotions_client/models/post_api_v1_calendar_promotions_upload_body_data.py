from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostApiV1CalendarPromotionsUploadBodyData")


@_attrs_define
class PostApiV1CalendarPromotionsUploadBodyData:
    """Dannye zaprosa

    Attributes:
        promotion_id (int | Unset): ID aktsii Example: 1.
        upload_now (bool | Unset): Ustanovit' skidku:
              - `true` — sejchas
              - `false` — v moment starta aktsii
             Example: True.
        nomenclatures (list[int] | Unset): Artikuly WB, kotorye mozhno dobavit' v aktsiju Example: [75632091, 31322455,
            642080796].
    """

    promotion_id: int | Unset = UNSET
    upload_now: bool | Unset = UNSET
    nomenclatures: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        promotion_id = self.promotion_id

        upload_now = self.upload_now

        nomenclatures: list[int] | Unset = UNSET
        if not isinstance(self.nomenclatures, Unset):
            nomenclatures = self.nomenclatures

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if promotion_id is not UNSET:
            field_dict["promotionID"] = promotion_id
        if upload_now is not UNSET:
            field_dict["uploadNow"] = upload_now
        if nomenclatures is not UNSET:
            field_dict["nomenclatures"] = nomenclatures

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        promotion_id = d.pop("promotionID", UNSET)

        upload_now = d.pop("uploadNow", UNSET)

        nomenclatures = cast(list[int], d.pop("nomenclatures", UNSET))

        post_api_v1_calendar_promotions_upload_body_data = cls(
            promotion_id=promotion_id,
            upload_now=upload_now,
            nomenclatures=nomenclatures,
        )

        post_api_v1_calendar_promotions_upload_body_data.additional_properties = d
        return post_api_v1_calendar_promotions_upload_body_data

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
