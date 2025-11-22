from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_shipping_office_metrics import TableShippingOfficeMetrics


T = TypeVar("T", bound="TableShippingOfficeItemOfficesItem")


@_attrs_define
class TableShippingOfficeItemOfficesItem:
    """
    Attributes:
        office_id (int): ID sklada Example: 123456.
        office_name (str): Nazvanie sklada Example: Koledino.
        metrics (TableShippingOfficeMetrics): Obschie metriki po regionam/skladam otgruzki
    """

    office_id: int
    office_name: str
    metrics: "TableShippingOfficeMetrics"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        office_id = self.office_id

        office_name = self.office_name

        metrics = self.metrics.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "officeID": office_id,
                "officeName": office_name,
                "metrics": metrics,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_shipping_office_metrics import TableShippingOfficeMetrics

        d = src_dict.copy()
        office_id = d.pop("officeID")

        office_name = d.pop("officeName")

        metrics = TableShippingOfficeMetrics.from_dict(d.pop("metrics"))

        table_shipping_office_item_offices_item = cls(
            office_id=office_id,
            office_name=office_name,
            metrics=metrics,
        )

        table_shipping_office_item_offices_item.additional_properties = d
        return table_shipping_office_item_offices_item

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
