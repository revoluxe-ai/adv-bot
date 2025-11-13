from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="V0GetConfigCategoriesResponse")


@_attrs_define
class V0GetConfigCategoriesResponse:
    """
    Example:
        {'id': 760, 'name': "Avtomobil'nye tovary", 'cpm_min': 112}

    Attributes:
        id (int): ID kategorii tovara
        name (str): Nazvanie kategorii tovara
        cpm_min (int): Minimal'no dopustimaja stavka
    """

    id: int
    name: str
    cpm_min: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        name = self.name

        cpm_min = self.cpm_min

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "cpm_min": cpm_min,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = d.pop("id")

        name = d.pop("name")

        cpm_min = d.pop("cpm_min")

        v0_get_config_categories_response = cls(
            id=id,
            name=name,
            cpm_min=cpm_min,
        )

        v0_get_config_categories_response.additional_properties = d
        return v0_get_config_categories_response

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
