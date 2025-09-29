from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1CountResponse200Adverts")


@_attrs_define
class GetAdvV1CountResponse200Adverts:
    """
    Attributes:
        type_ (Union[Unset, int]): <dl>
            <dt>Tip mediakampanii:</dt>
            <dd><code>1</code> — razmeschenie po dnjam</dd>
            <dd><code>2</code> — razmeschenie po prosmotram</dd>
            </dl>
        status (Union[Unset, int]): <dl>
            <dt>Status mediakampanii:</dt>
              <dd><code>1</code> — chernovik</dd>
              <dd><code>2</code> — moderatsija
              <dd><code>3</code> — otklonena (s vozmozhnost'ju vernut' na moderatsiju)</dd>
              <dd><code>4</code> — gotova k zapusku</dd>
              <dd><code>5</code> — zaplanirovana</dd>
              <dd><code>6</code> — na pokazah</dd>
              <dd><code>7</code> — zavershena</dd>
              <dd><code>8</code> — otmenena</dd>
              <dd><code>9</code> — priostanovlena prodavtsom</dd>
              <dd><code>10</code> — pauza po dnevnomu limitu</dd>
              <dd><code>11</code> — pauza</dd>
            </dl>
        count (Union[Unset, int]): Kolichestvo mediakampanij
    """

    type_: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    count: Union[Unset, int] = UNSET
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
