from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_api_v1_analytics_banned_products_blocked_response_200_report_item import (
        GetApiV1AnalyticsBannedProductsBlockedResponse200ReportItem,
    )


T = TypeVar("T", bound="GetApiV1AnalyticsBannedProductsBlockedResponse200")


@_attrs_define
class GetApiV1AnalyticsBannedProductsBlockedResponse200:
    """
    Attributes:
        report (Union[Unset, List['GetApiV1AnalyticsBannedProductsBlockedResponse200ReportItem']]): Report
    """

    report: Union[
        Unset, List["GetApiV1AnalyticsBannedProductsBlockedResponse200ReportItem"]
    ] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        report: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.report, Unset):
            report = []
            for report_item_data in self.report:
                report_item = report_item_data.to_dict()
                report.append(report_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if report is not UNSET:
            field_dict["report"] = report

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_api_v1_analytics_banned_products_blocked_response_200_report_item import (
            GetApiV1AnalyticsBannedProductsBlockedResponse200ReportItem,
        )

        d = src_dict.copy()
        report = []
        _report = d.pop("report", UNSET)
        for report_item_data in _report or []:
            report_item = (
                GetApiV1AnalyticsBannedProductsBlockedResponse200ReportItem.from_dict(
                    report_item_data
                )
            )

            report.append(report_item)

        get_api_v1_analytics_banned_products_blocked_response_200 = cls(
            report=report,
        )

        get_api_v1_analytics_banned_products_blocked_response_200.additional_properties = d
        return get_api_v1_analytics_banned_products_blocked_response_200

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
