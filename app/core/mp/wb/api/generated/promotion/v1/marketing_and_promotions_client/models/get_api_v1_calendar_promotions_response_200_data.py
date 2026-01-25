from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_api_v1_calendar_promotions_response_200_data_promotions_item import (
        GetApiV1CalendarPromotionsResponse200DataPromotionsItem,
    )


T = TypeVar("T", bound="GetApiV1CalendarPromotionsResponse200Data")


@_attrs_define
class GetApiV1CalendarPromotionsResponse200Data:
    """Response data

    Attributes:
        promotions (list[GetApiV1CalendarPromotionsResponse200DataPromotionsItem] | Unset): Promotions list
    """

    promotions: (
        list[GetApiV1CalendarPromotionsResponse200DataPromotionsItem] | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.get_api_v1_calendar_promotions_response_200_data_promotions_item import (
            GetApiV1CalendarPromotionsResponse200DataPromotionsItem,
        )

        promotions: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.promotions, Unset):
            promotions = []
            for promotions_item_data in self.promotions:
                promotions_item = promotions_item_data.to_dict()
                promotions.append(promotions_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if promotions is not UNSET:
            field_dict["promotions"] = promotions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_api_v1_calendar_promotions_response_200_data_promotions_item import (
            GetApiV1CalendarPromotionsResponse200DataPromotionsItem,
        )

        d = dict(src_dict)
        _promotions = d.pop("promotions", UNSET)
        promotions: (
            list[GetApiV1CalendarPromotionsResponse200DataPromotionsItem] | Unset
        ) = UNSET
        if _promotions is not UNSET:
            promotions = []
            for promotions_item_data in _promotions:
                promotions_item = (
                    GetApiV1CalendarPromotionsResponse200DataPromotionsItem.from_dict(
                        promotions_item_data
                    )
                )

                promotions.append(promotions_item)

        get_api_v1_calendar_promotions_response_200_data = cls(
            promotions=promotions,
        )

        get_api_v1_calendar_promotions_response_200_data.additional_properties = d
        return get_api_v1_calendar_promotions_response_200_data

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
