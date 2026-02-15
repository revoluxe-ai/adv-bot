from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1CountResponse200Adverts")


@_attrs_define
class GetAdvV1CountResponse200Adverts:
    """
    Attributes:
        type (Union[Unset, int]): Media campaign type:
            - `1` — daily basis
            - `2` — views basis
        status (Union[Unset, int]): Media campaign status:
              - `1` — template
              - `2` — moderation
              - `3` — rejected (with the possibility to resubmit for moderation)
              - `4` — ready for launch
              - `5` — scheduled
              - `6` — running
              - `7` — completed
              - `8` — declined
              - `9` — paused by seller
              - `10` — paused due to daily limit
              - `11` — paused
        count (Union[Unset, int]): Number of media campaigns
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
