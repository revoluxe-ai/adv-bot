from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar(
    "T",
    bound="GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem",
)


@_attrs_define
class GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem:
    """
    Attributes:
        condition (Union[Unset, str]): Tip [ranzhirovanija](https://seller.wildberries.ru/help-center/article/A-385):
              - `productsInPromotion` — prodvizhenie poluchat tovary prodavtsa, uchastvujuschie v aktsii
              - `calculateProducts` — prodvizhenie poluchat ljubye tovara prodavtsa, predlozhennye k uchastiju v aktsii
              - `allProducts` — prodvizhenie poluchat vse tovary prodavtsa
        participation_rate (Union[Unset, int]): Kolichestvo tovarov prodavtsa dlja perehoda na sledujuschij uroven'
            ranzhirovanija, %
        boost (Union[Unset, int]): Tekuschij uroven' podnjatija v poiske, %
    """

    condition: Union[Unset, str] = UNSET
    participation_rate: Union[Unset, int] = UNSET
    boost: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        condition = self.condition

        participation_rate = self.participation_rate

        boost = self.boost

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if condition is not UNSET:
            field_dict["condition"] = condition
        if participation_rate is not UNSET:
            field_dict["participationRate"] = participation_rate
        if boost is not UNSET:
            field_dict["boost"] = boost

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        condition = d.pop("condition", UNSET)

        participation_rate = d.pop("participationRate", UNSET)

        boost = d.pop("boost", UNSET)

        get_api_v1_calendar_promotions_details_response_200_data_promotions_item_ranging_item = cls(
            condition=condition,
            participation_rate=participation_rate,
            boost=boost,
        )

        get_api_v1_calendar_promotions_details_response_200_data_promotions_item_ranging_item.additional_properties = d
        return get_api_v1_calendar_promotions_details_response_200_data_promotions_item_ranging_item

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
