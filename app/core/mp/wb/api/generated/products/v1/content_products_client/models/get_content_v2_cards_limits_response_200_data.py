from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetContentV2CardsLimitsResponse200Data")


@_attrs_define
class GetContentV2CardsLimitsResponse200Data:
    """
    Attributes:
        free_limits (int | Unset): Kolichestvo besplatnyh limitov
        paid_limits (int | Unset): Kolichestvo oplachennyh limitov
    """

    free_limits: int | Unset = UNSET
    paid_limits: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        free_limits = self.free_limits

        paid_limits = self.paid_limits

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if free_limits is not UNSET:
            field_dict["freeLimits"] = free_limits
        if paid_limits is not UNSET:
            field_dict["paidLimits"] = paid_limits

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        free_limits = d.pop("freeLimits", UNSET)

        paid_limits = d.pop("paidLimits", UNSET)

        get_content_v2_cards_limits_response_200_data = cls(
            free_limits=free_limits,
            paid_limits=paid_limits,
        )

        get_content_v2_cards_limits_response_200_data.additional_properties = d
        return get_content_v2_cards_limits_response_200_data

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
