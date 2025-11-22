from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_history_response_data_item_history_item import (
        NmReportDetailHistoryResponseDataItemHistoryItem,
    )


T = TypeVar("T", bound="NmReportDetailHistoryResponseDataItem")


@_attrs_define
class NmReportDetailHistoryResponseDataItem:
    """
    Attributes:
        nm_id (Union[Unset, int]): Artikul WB Example: 1234567.
        imt_name (Union[Unset, str]): Naimenovanie kartochki tovara Example: Naimenovanie kartochki tovara.
        vendor_code (Union[Unset, str]): Artikul prodavtsa Example: supplierVendor.
        history (Union[Unset, List['NmReportDetailHistoryResponseDataItemHistoryItem']]):
    """

    nm_id: Union[Unset, int] = UNSET
    imt_name: Union[Unset, str] = UNSET
    vendor_code: Union[Unset, str] = UNSET
    history: Union[Unset, List["NmReportDetailHistoryResponseDataItemHistoryItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        imt_name = self.imt_name

        vendor_code = self.vendor_code

        history: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.history, Unset):
            history = []
            for history_item_data in self.history:
                history_item = history_item_data.to_dict()
                history.append(history_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if imt_name is not UNSET:
            field_dict["imtName"] = imt_name
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if history is not UNSET:
            field_dict["history"] = history

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_history_response_data_item_history_item import (
            NmReportDetailHistoryResponseDataItemHistoryItem,
        )

        d = src_dict.copy()
        nm_id = d.pop("nmID", UNSET)

        imt_name = d.pop("imtName", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        history = []
        _history = d.pop("history", UNSET)
        for history_item_data in _history or []:
            history_item = NmReportDetailHistoryResponseDataItemHistoryItem.from_dict(history_item_data)

            history.append(history_item)

        nm_report_detail_history_response_data_item = cls(
            nm_id=nm_id,
            imt_name=imt_name,
            vendor_code=vendor_code,
            history=history,
        )

        nm_report_detail_history_response_data_item.additional_properties = d
        return nm_report_detail_history_response_data_item

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
