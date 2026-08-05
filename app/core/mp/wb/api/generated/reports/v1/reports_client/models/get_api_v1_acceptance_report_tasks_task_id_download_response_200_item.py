import datetime
from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item")


@_attrs_define
class GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item:
    """
    Attributes:
        count (Union[Unset, int]): Number of items Example: 40.
        gi_create_date (Union[Unset, datetime.date]): Shipment creation date Example: 2025-03-04.
        income_id (Union[Unset, int]): Shipment number Example: 11834106.
        nm_id (Union[Unset, int]): Wildberries item number Example: 123456789.
        shk_create_date (Union[Unset, datetime.date]): Receiving date Example: 2025-03-14.
        subject_name (Union[Unset, str]): Subcategory Example: Добавки пищевые.
        total (Union[Unset, float]): Receiving cost, ₽ with kopecks Example: 873.04.
    """

    count: Union[Unset, int] = UNSET
    gi_create_date: Union[Unset, datetime.date] = UNSET
    income_id: Union[Unset, int] = UNSET
    nm_id: Union[Unset, int] = UNSET
    shk_create_date: Union[Unset, datetime.date] = UNSET
    subject_name: Union[Unset, str] = UNSET
    total: Union[Unset, float] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        count = self.count

        gi_create_date: Union[Unset, str] = UNSET
        if not isinstance(self.gi_create_date, Unset):
            gi_create_date = self.gi_create_date.isoformat()

        income_id = self.income_id

        nm_id = self.nm_id

        shk_create_date: Union[Unset, str] = UNSET
        if not isinstance(self.shk_create_date, Unset):
            shk_create_date = self.shk_create_date.isoformat()

        subject_name = self.subject_name

        total = self.total

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if count is not UNSET:
            field_dict["count"] = count
        if gi_create_date is not UNSET:
            field_dict["giCreateDate"] = gi_create_date
        if income_id is not UNSET:
            field_dict["incomeId"] = income_id
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if shk_create_date is not UNSET:
            field_dict["shkCreateDate"] = shk_create_date
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if total is not UNSET:
            field_dict["total"] = total

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        count = d.pop("count", UNSET)

        _gi_create_date = d.pop("giCreateDate", UNSET)
        gi_create_date: Union[Unset, datetime.date]
        if isinstance(_gi_create_date, Unset):
            gi_create_date = UNSET
        else:
            gi_create_date = isoparse(_gi_create_date).date()

        income_id = d.pop("incomeId", UNSET)

        nm_id = d.pop("nmID", UNSET)

        _shk_create_date = d.pop("shkCreateDate", UNSET)
        shk_create_date: Union[Unset, datetime.date]
        if isinstance(_shk_create_date, Unset):
            shk_create_date = UNSET
        else:
            shk_create_date = isoparse(_shk_create_date).date()

        subject_name = d.pop("subjectName", UNSET)

        total = d.pop("total", UNSET)

        get_api_v1_acceptance_report_tasks_task_id_download_response_200_item = cls(
            count=count,
            gi_create_date=gi_create_date,
            income_id=income_id,
            nm_id=nm_id,
            shk_create_date=shk_create_date,
            subject_name=subject_name,
            total=total,
        )

        get_api_v1_acceptance_report_tasks_task_id_download_response_200_item.additional_properties = d
        return get_api_v1_acceptance_report_tasks_task_id_download_response_200_item

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
