from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NmReportDetailRequestPeriod")


@_attrs_define
class NmReportDetailRequestPeriod:
    """Period

    Attributes:
        begin (Union[Unset, str]): Nachalo perioda Example: 2023-06-01 20:05:32.
        end (Union[Unset, str]): Konets perioda Example: 2024-03-01 20:05:32.
    """

    begin: Union[Unset, str] = UNSET
    end: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        begin = self.begin

        end = self.end

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if begin is not UNSET:
            field_dict["begin"] = begin
        if end is not UNSET:
            field_dict["end"] = end

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        begin = d.pop("begin", UNSET)

        end = d.pop("end", UNSET)

        nm_report_detail_request_period = cls(
            begin=begin,
            end=end,
        )

        nm_report_detail_request_period.additional_properties = d
        return nm_report_detail_request_period

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
