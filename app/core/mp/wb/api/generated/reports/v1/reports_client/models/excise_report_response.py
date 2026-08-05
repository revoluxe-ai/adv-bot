from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.models_excise_report_response import ModelsExciseReportResponse


T = TypeVar("T", bound="ExciseReportResponse")


@_attrs_define
class ExciseReportResponse:
    """
    Attributes:
        response (Union[Unset, ModelsExciseReportResponse]):
    """

    response: Union[Unset, "ModelsExciseReportResponse"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        response: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.response, Unset):
            response = self.response.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if response is not UNSET:
            field_dict["response"] = response

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.models_excise_report_response import ModelsExciseReportResponse

        d = src_dict.copy()
        _response = d.pop("response", UNSET)
        response: Union[Unset, ModelsExciseReportResponse]
        if isinstance(_response, Unset):
            response = UNSET
        else:
            response = ModelsExciseReportResponse.from_dict(_response)

        excise_report_response = cls(
            response=response,
        )

        excise_report_response.additional_properties = d
        return excise_report_response

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
