from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar(
    "T",
    bound="GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200ItemWarehousesItem",
)


@_attrs_define
class GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200ItemWarehousesItem:
    """
    Attributes:
        warehouse_name (Union[Unset, str]): Warehouse name Example: Невинномысск.
        quantity (Union[Unset, int]): Quantity
             Example: 134.
    """

    warehouse_name: Union[Unset, str] = UNSET
    quantity: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        warehouse_name = self.warehouse_name

        quantity = self.quantity

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if warehouse_name is not UNSET:
            field_dict["warehouseName"] = warehouse_name
        if quantity is not UNSET:
            field_dict["quantity"] = quantity

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        warehouse_name = d.pop("warehouseName", UNSET)

        quantity = d.pop("quantity", UNSET)

        get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item_warehouses_item = cls(
            warehouse_name=warehouse_name,
            quantity=quantity,
        )

        get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item_warehouses_item.additional_properties = d
        return get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item_warehouses_item

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
