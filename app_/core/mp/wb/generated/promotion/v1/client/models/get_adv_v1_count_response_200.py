from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v1_count_response_200_adverts import (
        GetAdvV1CountResponse200Adverts,
    )


T = TypeVar("T", bound="GetAdvV1CountResponse200")


@_attrs_define
class GetAdvV1CountResponse200:
    """
    Attributes:
        all_ (Union[Unset, int]): Obschee kolichestvo mediakampanij vseh statusov i tipov
        adverts (Union[Unset, GetAdvV1CountResponse200Adverts]):
    """

    all_: Union[Unset, int] = UNSET
    adverts: Union[Unset, "GetAdvV1CountResponse200Adverts"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        all_ = self.all_

        adverts: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.adverts, Unset):
            adverts = self.adverts.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if all_ is not UNSET:
            field_dict["all"] = all_
        if adverts is not UNSET:
            field_dict["adverts"] = adverts

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v1_count_response_200_adverts import (
            GetAdvV1CountResponse200Adverts,
        )

        d = dict(src_dict)
        all_ = d.pop("all", UNSET)

        _adverts = d.pop("adverts", UNSET)
        adverts: Union[Unset, GetAdvV1CountResponse200Adverts]
        if isinstance(_adverts, Unset):
            adverts = UNSET
        else:
            adverts = GetAdvV1CountResponse200Adverts.from_dict(_adverts)

        get_adv_v1_count_response_200 = cls(
            all_=all_,
            adverts=adverts,
        )

        get_adv_v1_count_response_200.additional_properties = d
        return get_adv_v1_count_response_200

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
