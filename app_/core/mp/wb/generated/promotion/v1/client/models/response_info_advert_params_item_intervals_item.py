from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponseInfoAdvertParamsItemIntervalsItem")


@_attrs_define
class ResponseInfoAdvertParamsItemIntervalsItem:
    """
    Attributes:
        begin (Union[Unset, int]): Vremja nachala pokazov
        end (Union[Unset, int]): Vremja okonchanija pokazov
    """

    begin: Union[Unset, int] = UNSET
    end: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        begin = self.begin

        end = self.end

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if begin is not UNSET:
            field_dict["begin"] = begin
        if end is not UNSET:
            field_dict["end"] = end

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        begin = d.pop("begin", UNSET)

        end = d.pop("end", UNSET)

        response_info_advert_params_item_intervals_item = cls(
            begin=begin,
            end=end,
        )

        response_info_advert_params_item_intervals_item.additional_properties = d
        return response_info_advert_params_item_intervals_item

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
