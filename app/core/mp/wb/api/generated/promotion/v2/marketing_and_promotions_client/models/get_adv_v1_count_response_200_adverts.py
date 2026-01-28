from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1CountResponse200Adverts")


@_attrs_define
class GetAdvV1CountResponse200Adverts:
    """
    Attributes:
        type_ (int | Unset): Tip mediakampanii:
            - `1` — razmeschenie po dnjam
            - `2` — razmeschenie po prosmotram
        status (int | Unset): Status mediakampanii:
              - `1` — chernovik
              - `2` — moderatsija
              - `3` — otklonena (s vozmozhnost'ju vernut' na moderatsiju)
              - `4` — gotova k zapusku
              - `5` — zaplanirovana
              - `6` — na pokazah
              - `7` — zavershena
              - `8` — otmenena
              - `9` — priostanovlena prodavtsom
              - `10` — pauza po dnevnomu limitu
              - `11` — pauza
        count (int | Unset): Kolichestvo mediakampanij
    """

    type_: int | Unset = UNSET
    status: int | Unset = UNSET
    count: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        status = self.status

        count = self.count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if type_ is not UNSET:
            field_dict["type"] = type_
        if status is not UNSET:
            field_dict["status"] = status
        if count is not UNSET:
            field_dict["count"] = count

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = d.pop("type", UNSET)

        status = d.pop("status", UNSET)

        count = d.pop("count", UNSET)

        get_adv_v1_count_response_200_adverts = cls(
            type_=type_,
            status=status,
            count=count,
        )

        get_adv_v1_count_response_200_adverts.additional_properties = d
        return get_adv_v1_count_response_200_adverts

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
