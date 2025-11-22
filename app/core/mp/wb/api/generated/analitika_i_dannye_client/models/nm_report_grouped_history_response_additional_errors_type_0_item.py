from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NmReportGroupedHistoryResponseAdditionalErrorsType0Item")


@_attrs_define
class NmReportGroupedHistoryResponseAdditionalErrorsType0Item:
    """
    Attributes:
        field (Union[Unset, str]): Struktura, gde dopuschena oshibka
        description (Union[Unset, str]): Opisanie
    """

    field: Union[Unset, str] = UNSET
    description: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        field = self.field

        description = self.description

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if field is not UNSET:
            field_dict["field"] = field
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        field = d.pop("field", UNSET)

        description = d.pop("description", UNSET)

        nm_report_grouped_history_response_additional_errors_type_0_item = cls(
            field=field,
            description=description,
        )

        nm_report_grouped_history_response_additional_errors_type_0_item.additional_properties = d
        return nm_report_grouped_history_response_additional_errors_type_0_item

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
