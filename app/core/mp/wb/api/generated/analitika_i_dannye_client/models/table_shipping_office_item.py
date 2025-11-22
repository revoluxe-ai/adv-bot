from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_shipping_office_item_offices_item import TableShippingOfficeItemOfficesItem
    from ..models.table_shipping_office_metrics import TableShippingOfficeMetrics


T = TypeVar("T", bound="TableShippingOfficeItem")


@_attrs_define
class TableShippingOfficeItem:
    """Dannye po regionu otgruzki

    Attributes:
        region_name (str): Region otgruzki Example: Tsentral'nyj.
        metrics (TableShippingOfficeMetrics): Obschie metriki po regionam/skladam otgruzki
        offices (List['TableShippingOfficeItemOfficesItem']): Dannye po skladam
    """

    region_name: str
    metrics: "TableShippingOfficeMetrics"
    offices: List["TableShippingOfficeItemOfficesItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        region_name = self.region_name

        metrics = self.metrics.to_dict()

        offices = []
        for offices_item_data in self.offices:
            offices_item = offices_item_data.to_dict()
            offices.append(offices_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "regionName": region_name,
                "metrics": metrics,
                "offices": offices,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_shipping_office_item_offices_item import TableShippingOfficeItemOfficesItem
        from ..models.table_shipping_office_metrics import TableShippingOfficeMetrics

        d = src_dict.copy()
        region_name = d.pop("regionName")

        metrics = TableShippingOfficeMetrics.from_dict(d.pop("metrics"))

        offices = []
        _offices = d.pop("offices")
        for offices_item_data in _offices:
            offices_item = TableShippingOfficeItemOfficesItem.from_dict(offices_item_data)

            offices.append(offices_item)

        table_shipping_office_item = cls(
            region_name=region_name,
            metrics=metrics,
            offices=offices,
        )

        table_shipping_office_item.additional_properties = d
        return table_shipping_office_item

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
