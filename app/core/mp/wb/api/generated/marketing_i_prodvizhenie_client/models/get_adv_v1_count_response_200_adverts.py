from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1CountResponse200Adverts")


@_attrs_define
class GetAdvV1CountResponse200Adverts:
    """
    Attributes:
        type (Union[Unset, int]): Tip mediakampanii:
            - `1` — razmeschenie po dnjam
            - `2` — razmeschenie po prosmotram
        status (Union[Unset, int]): Status mediakampanii:
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
        count (Union[Unset, int]): Kolichestvo mediakampanij
    """

    type: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    count: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        type = self.type

        status = self.status

        count = self.count

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if type is not UNSET:
            field_dict["type"] = type
        if status is not UNSET:
            field_dict["status"] = status
        if count is not UNSET:
            field_dict["count"] = count

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        type = d.pop("type", UNSET)

        status = d.pop("status", UNSET)

        count = d.pop("count", UNSET)

        get_adv_v1_count_response_200_adverts = cls(
            type=type,
            status=status,
            count=count,
        )

        get_adv_v1_count_response_200_adverts.additional_properties = d
        return get_adv_v1_count_response_200_adverts

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
