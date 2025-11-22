from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TableSearchTextItemFrequency")


@_attrs_define
class TableSearchTextItemFrequency:
    """Kolichestvo obraschenij s poiskovym zaprosom

    Attributes:
        current (int): Tekuschee kolichestvo Example: 5.
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

        table_search_text_item_frequency = cls(
            current=current,
            dynamics=dynamics,
        )

        table_search_text_item_frequency.additional_properties = d
        return table_search_text_item_frequency

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
