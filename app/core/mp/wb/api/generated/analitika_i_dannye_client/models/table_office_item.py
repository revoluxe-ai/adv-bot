from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_common_metrics import TableCommonMetrics


T = TypeVar("T", bound="TableOfficeItem")


@_attrs_define
class TableOfficeItem:
    """Dannye po skladu

    Attributes:
        region_name (str): Region otgruzki Example: Tsentral'nyj.
        office_id (int): ID sklada Example: 123456.
        office_name (str): Nazvanie sklada Example: Koledino.
        metrics (TableCommonMetrics): Metriki
    """

    region_name: str
    office_id: int
    office_name: str
    metrics: "TableCommonMetrics"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        region_name = self.region_name

        office_id = self.office_id

        office_name = self.office_name

        metrics = self.metrics.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "regionName": region_name,
                "officeID": office_id,
                "officeName": office_name,
                "metrics": metrics,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_common_metrics import TableCommonMetrics

        d = src_dict.copy()
        region_name = d.pop("regionName")

        office_id = d.pop("officeID")

        office_name = d.pop("officeName")

        metrics = TableCommonMetrics.from_dict(d.pop("metrics"))

        table_office_item = cls(
            region_name=region_name,
            office_id=office_id,
            office_name=office_name,
            metrics=metrics,
        )

        table_office_item.additional_properties = d
        return table_office_item

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
