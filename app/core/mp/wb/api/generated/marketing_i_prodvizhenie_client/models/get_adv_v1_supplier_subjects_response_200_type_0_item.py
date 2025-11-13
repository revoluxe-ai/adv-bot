from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1SupplierSubjectsResponse200Type0Item")


@_attrs_define
class GetAdvV1SupplierSubjectsResponse200Type0Item:
    """
    Attributes:
        id (Union[Unset, int]): ID predmeta
        name (Union[Unset, str]): Predmet
        count (Union[Unset, int]): Kolichestvo Artikulov WB (`nmId`) s takim predmetom.
    """

    id: Union[Unset, int] = UNSET
    name: Union[Unset, str] = UNSET
    count: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        name = self.name

        count = self.count

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if count is not UNSET:
            field_dict["count"] = count

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        count = d.pop("count", UNSET)

        get_adv_v1_supplier_subjects_response_200_type_0_item = cls(
            id=id,
            name=name,
            count=count,
        )

        get_adv_v1_supplier_subjects_response_200_type_0_item.additional_properties = d
        return get_adv_v1_supplier_subjects_response_200_type_0_item

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
