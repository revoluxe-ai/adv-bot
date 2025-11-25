import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="NmReportGetReportsResponseDataItem")


@_attrs_define
class NmReportGetReportsResponseDataItem:
    """
    Attributes:
        id (str): ID otcheta Example: 06eae887-9d9f-491f-b16a-bb1766fcb8d2.
        created_at (datetime.datetime): Data i vremja zavershenija generatsii Example: 2024-06-26 20:05:32.
        status (str): Status otcheta:

            * `WAITING` — v ocheredi na obrabotku
            * `PROCESSING` — generiruetsja
            * `SUCCESS —` gotov
            * `RETRY` — ozhidaet povtornoj obrabotki
            * `FAILED` — ne poluchilos' sgenerirovat', sgenerirujte povtorno
             Example: SUCCESS.
        name (str): Nazvanie otcheta Example: Card report.
        size (int): Razmer otcheta, B Example: 123.
        start_date (datetime.date): Nachalo perioda Example: 2024-06-21.
        end_date (datetime.date): Konets perioda Example: 2024-06-23.
    """

    id: str
    created_at: datetime.datetime
    status: str
    name: str
    size: int
    start_date: datetime.date
    end_date: datetime.date
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        created_at = self.created_at.isoformat()

        status = self.status

        name = self.name

        size = self.size

        start_date = self.start_date.isoformat()

        end_date = self.end_date.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "createdAt": created_at,
                "status": status,
                "name": name,
                "size": size,
                "startDate": start_date,
                "endDate": end_date,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = d.pop("id")

        created_at = isoparse(d.pop("createdAt"))

        status = d.pop("status")

        name = d.pop("name")

        size = d.pop("size")

        start_date = isoparse(d.pop("startDate")).date()

        end_date = isoparse(d.pop("endDate")).date()

        nm_report_get_reports_response_data_item = cls(
            id=id,
            created_at=created_at,
            status=status,
            name=name,
            size=size,
            start_date=start_date,
            end_date=end_date,
        )

        nm_report_get_reports_response_data_item.additional_properties = d
        return nm_report_get_reports_response_data_item

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
