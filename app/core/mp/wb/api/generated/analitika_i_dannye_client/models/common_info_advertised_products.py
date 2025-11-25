from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CommonInfoAdvertisedProducts")


@_attrs_define
class CommonInfoAdvertisedProducts:
    """Kolichestvo tovarov v reklame

    Attributes:
        current (int): Tekuschee kolichestvo tovarov v reklame Example: 5.
        dynamics (Union[Unset, int]): Dinamika po sravneniju s predyduschim periodom, % Example: 50.
    """

    current: int
    dynamics: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current = self.current

        dynamics = self.dynamics

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "current": current,
            }
        )
        if dynamics is not UNSET:
            field_dict["dynamics"] = dynamics

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        current = d.pop("current")

        dynamics = d.pop("dynamics", UNSET)

        common_info_advertised_products = cls(
            current=current,
            dynamics=dynamics,
        )

        common_info_advertised_products.additional_properties = d
        return common_info_advertised_products

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
