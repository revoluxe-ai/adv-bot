from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.models_excise_report_response_data_item import (
        ModelsExciseReportResponseDataItem,
    )


T = TypeVar("T", bound="ModelsExciseReportResponse")


@_attrs_define
class ModelsExciseReportResponse:
    """
    Attributes:
        data (Union[Unset, List['ModelsExciseReportResponseDataItem']]):
    """

    data: Union[Unset, List["ModelsExciseReportResponseDataItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.data, Unset):
            data = []
            for (
                componentsschemasmodels_excise_report_response_data_item_data
            ) in self.data:
                componentsschemasmodels_excise_report_response_data_item = componentsschemasmodels_excise_report_response_data_item_data.to_dict()
                data.append(componentsschemasmodels_excise_report_response_data_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.models_excise_report_response_data_item import (
            ModelsExciseReportResponseDataItem,
        )

        d = src_dict.copy()
        data = []
        _data = d.pop("data", UNSET)
        for componentsschemasmodels_excise_report_response_data_item_data in (
            _data or []
        ):
            componentsschemasmodels_excise_report_response_data_item = (
                ModelsExciseReportResponseDataItem.from_dict(
                    componentsschemasmodels_excise_report_response_data_item_data
                )
            )

            data.append(componentsschemasmodels_excise_report_response_data_item)

        models_excise_report_response = cls(
            data=data,
        )

        models_excise_report_response.additional_properties = d
        return models_excise_report_response

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
