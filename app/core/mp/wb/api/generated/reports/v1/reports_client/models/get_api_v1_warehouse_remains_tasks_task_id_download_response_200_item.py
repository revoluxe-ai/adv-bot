from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item_warehouses_item import (
        GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200ItemWarehousesItem,
    )


T = TypeVar("T", bound="GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200Item")


@_attrs_define
class GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200Item:
    """
    Attributes:
        brand (Union[Unset, str]): Brand Example: Wonderful.
        subject_name (Union[Unset, str]): Subcategory name Example: Фотоальбомы.
        vendor_code (Union[Unset, str]): Seller item number Example: 41058/прозрачный.
        nm_id (Union[Unset, int]): WB item number Example: 183804172.
        barcode (Union[Unset, str]): Barcode Example: 2037031652319.
        tech_size (Union[Unset, str]): Size Example: 0.
        volume (Union[Unset, float]): Volume, L Example: 1.33.
        warehouses (Union[Unset, List['GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200ItemWarehousesItem']]):
            Inventory and to and from the client. It will be included in the response only if `quantity` is non-zero
    """

    brand: Union[Unset, str] = UNSET
    subject_name: Union[Unset, str] = UNSET
    vendor_code: Union[Unset, str] = UNSET
    nm_id: Union[Unset, int] = UNSET
    barcode: Union[Unset, str] = UNSET
    tech_size: Union[Unset, str] = UNSET
    volume: Union[Unset, float] = UNSET
    warehouses: Union[
        Unset,
        List[
            "GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200ItemWarehousesItem"
        ],
    ] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        brand = self.brand

        subject_name = self.subject_name

        vendor_code = self.vendor_code

        nm_id = self.nm_id

        barcode = self.barcode

        tech_size = self.tech_size

        volume = self.volume

        warehouses: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.warehouses, Unset):
            warehouses = []
            for warehouses_item_data in self.warehouses:
                warehouses_item = warehouses_item_data.to_dict()
                warehouses.append(warehouses_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if brand is not UNSET:
            field_dict["brand"] = brand
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if barcode is not UNSET:
            field_dict["barcode"] = barcode
        if tech_size is not UNSET:
            field_dict["techSize"] = tech_size
        if volume is not UNSET:
            field_dict["volume"] = volume
        if warehouses is not UNSET:
            field_dict["warehouses"] = warehouses

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item_warehouses_item import (
            GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200ItemWarehousesItem,
        )

        d = src_dict.copy()
        brand = d.pop("brand", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        nm_id = d.pop("nmId", UNSET)

        barcode = d.pop("barcode", UNSET)

        tech_size = d.pop("techSize", UNSET)

        volume = d.pop("volume", UNSET)

        warehouses = []
        _warehouses = d.pop("warehouses", UNSET)
        for warehouses_item_data in _warehouses or []:
            warehouses_item = GetApiV1WarehouseRemainsTasksTaskIdDownloadResponse200ItemWarehousesItem.from_dict(
                warehouses_item_data
            )

            warehouses.append(warehouses_item)

        get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item = cls(
            brand=brand,
            subject_name=subject_name,
            vendor_code=vendor_code,
            nm_id=nm_id,
            barcode=barcode,
            tech_size=tech_size,
            volume=volume,
            warehouses=warehouses,
        )

        get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item.additional_properties = d
        return get_api_v1_warehouse_remains_tasks_task_id_download_response_200_item

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
