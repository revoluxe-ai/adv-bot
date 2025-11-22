from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.table_office_item import TableOfficeItem
    from ..models.table_size_response_sizes_item_metrics import TableSizeResponseSizesItemMetrics


T = TypeVar("T", bound="TableSizeResponseSizesItem")


@_attrs_define
class TableSizeResponseSizesItem:
    """
    Attributes:
        name (str): Nazvanie razmera Example: 50.
        chrt_id (int): ID razmera Example: 123321.
        metrics (TableSizeResponseSizesItemMetrics): Metriki razmera
        offices (Union[Unset, List['TableOfficeItem']]): Sklady
    """

    name: str
    chrt_id: int
    metrics: "TableSizeResponseSizesItemMetrics"
    offices: Union[Unset, List["TableOfficeItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        chrt_id = self.chrt_id

        metrics = self.metrics.to_dict()

        offices: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.offices, Unset):
            offices = []
            for offices_item_data in self.offices:
                offices_item = offices_item_data.to_dict()
                offices.append(offices_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "chrtID": chrt_id,
                "metrics": metrics,
            }
        )
        if offices is not UNSET:
            field_dict["offices"] = offices

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_office_item import TableOfficeItem
        from ..models.table_size_response_sizes_item_metrics import TableSizeResponseSizesItemMetrics

        d = src_dict.copy()
        name = d.pop("name")

        chrt_id = d.pop("chrtID")

        metrics = TableSizeResponseSizesItemMetrics.from_dict(d.pop("metrics"))

        offices = []
        _offices = d.pop("offices", UNSET)
        for offices_item_data in _offices or []:
            offices_item = TableOfficeItem.from_dict(offices_item_data)

            offices.append(offices_item)

        table_size_response_sizes_item = cls(
            name=name,
            chrt_id=chrt_id,
            metrics=metrics,
            offices=offices,
        )

        table_size_response_sizes_item.additional_properties = d
        return table_size_response_sizes_item

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
