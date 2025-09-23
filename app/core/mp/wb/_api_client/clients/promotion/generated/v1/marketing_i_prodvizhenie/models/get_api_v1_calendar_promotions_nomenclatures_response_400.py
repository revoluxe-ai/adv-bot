from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetApiV1CalendarPromotionsNomenclaturesResponse400")


@_attrs_define
class GetApiV1CalendarPromotionsNomenclaturesResponse400:
    """
    Attributes:
        error_text (Union[Unset, str]): Tekst oshibki Example: Invalid query params.
    """

    error_text: Union[Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        error_text = self.error_text

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if error_text is not UNSET:
            field_dict["errorText"] = error_text

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        error_text = d.pop("errorText", UNSET)

        get_api_v1_calendar_promotions_nomenclatures_response_400 = cls(
            error_text=error_text,
        )

        get_api_v1_calendar_promotions_nomenclatures_response_400.additional_properties = (
            d
        )
        return get_api_v1_calendar_promotions_nomenclatures_response_400

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
