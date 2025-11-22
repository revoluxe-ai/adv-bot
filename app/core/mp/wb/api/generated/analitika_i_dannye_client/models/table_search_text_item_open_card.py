from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TableSearchTextItemOpenCard")


@_attrs_define
class TableSearchTextItemOpenCard:
    """Kolichestvo perehodov v kartochku tovara iz poiska

    Attributes:
        current (int): Tekuschee kolichestvo perehodov Example: 5.
        percentile (int): Protsent, na kotoryj pokazatel' kolichestva otkrytij kartochki tovara vyshe, chem u kartochek
            konkurentov po poiskovomu zaprosu Example: 50.
        dynamics (Union[Unset, int]): Dinamika po sravneniju s predyduschim periodom, % Example: 50.
    """

    current: int
    percentile: int
    dynamics: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current = self.current

        percentile = self.percentile

        dynamics = self.dynamics

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "current": current,
                "percentile": percentile,
            }
        )
        if dynamics is not UNSET:
            field_dict["dynamics"] = dynamics

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        current = d.pop("current")

        percentile = d.pop("percentile")

        dynamics = d.pop("dynamics", UNSET)

        table_search_text_item_open_card = cls(
            current=current,
            percentile=percentile,
            dynamics=dynamics,
        )

        table_search_text_item_open_card.additional_properties = d
        return table_search_text_item_open_card

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
