from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CommonInfoSupplierRating")


@_attrs_define
class CommonInfoSupplierRating:
    """Rejting prodavtsa

    Attributes:
        current (float): Tekuschij rejting prodavtsa Example: 5.3.
        dynamics (Union[Unset, float]): Dinamika po sravneniju s predyduschim periodom, % Example: 5.4.
    """

    current: float
    dynamics: Union[Unset, float] = UNSET
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

        common_info_supplier_rating = cls(
            current=current,
            dynamics=dynamics,
        )

        common_info_supplier_rating.additional_properties = d
        return common_info_supplier_rating

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
