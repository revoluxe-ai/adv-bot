from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_history_response_additional_errors_type_0_item import (
        NmReportDetailHistoryResponseAdditionalErrorsType0Item,
    )
    from ..models.nm_report_detail_history_response_data_item import NmReportDetailHistoryResponseDataItem


T = TypeVar("T", bound="NmReportDetailHistoryResponse")


@_attrs_define
class NmReportDetailHistoryResponse:
    """
    Attributes:
        data (Union[Unset, List['NmReportDetailHistoryResponseDataItem']]):
        error (Union[Unset, bool]): Flag oshibki
        error_text (Union[Unset, str]): Opisanie oshibki
        additional_errors (Union[List['NmReportDetailHistoryResponseAdditionalErrorsType0Item'], None, Unset]):
            Dopolnitel'nye oshibki
    """

    data: Union[Unset, List["NmReportDetailHistoryResponseDataItem"]] = UNSET
    error: Union[Unset, bool] = UNSET
    error_text: Union[Unset, str] = UNSET
    additional_errors: Union[List["NmReportDetailHistoryResponseAdditionalErrorsType0Item"], None, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.data, Unset):
            data = []
            for data_item_data in self.data:
                data_item = data_item_data.to_dict()
                data.append(data_item)

        error = self.error

        error_text = self.error_text

        additional_errors: Union[List[Dict[str, Any]], None, Unset]
        if isinstance(self.additional_errors, Unset):
            additional_errors = UNSET
        elif isinstance(self.additional_errors, list):
            additional_errors = UNSET
            if not isinstance(self.additional_errors, Unset):
                additional_errors = []
                for additional_errors_type_0_item_data in self.additional_errors:
                    additional_errors_type_0_item = additional_errors_type_0_item_data.to_dict()
                    additional_errors.append(additional_errors_type_0_item)

        else:
            additional_errors = self.additional_errors

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data
        if error is not UNSET:
            field_dict["error"] = error
        if error_text is not UNSET:
            field_dict["errorText"] = error_text
        if additional_errors is not UNSET:
            field_dict["additionalErrors"] = additional_errors

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_history_response_additional_errors_type_0_item import (
            NmReportDetailHistoryResponseAdditionalErrorsType0Item,
        )
        from ..models.nm_report_detail_history_response_data_item import NmReportDetailHistoryResponseDataItem

        d = src_dict.copy()
        data = []
        _data = d.pop("data", UNSET)
        for data_item_data in _data or []:
            data_item = NmReportDetailHistoryResponseDataItem.from_dict(data_item_data)

            data.append(data_item)

        error = d.pop("error", UNSET)

        error_text = d.pop("errorText", UNSET)

        def _parse_additional_errors(
            data: object
        ) -> Union[List["NmReportDetailHistoryResponseAdditionalErrorsType0Item"], None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                additional_errors_type_0 = UNSET
                _additional_errors_type_0 = data
                for additional_errors_type_0_item_data in _additional_errors_type_0 or []:
                    additional_errors_type_0_item = NmReportDetailHistoryResponseAdditionalErrorsType0Item.from_dict(
                        additional_errors_type_0_item_data
                    )

                    additional_errors_type_0.append(additional_errors_type_0_item)

                return additional_errors_type_0
            except:  # noqa: E722
                pass
            return cast(Union[List["NmReportDetailHistoryResponseAdditionalErrorsType0Item"], None, Unset], data)

        additional_errors = _parse_additional_errors(d.pop("additionalErrors", UNSET))

        nm_report_detail_history_response = cls(
            data=data,
            error=error,
            error_text=error_text,
            additional_errors=additional_errors,
        )

        nm_report_detail_history_response.additional_properties = d
        return nm_report_detail_history_response

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
