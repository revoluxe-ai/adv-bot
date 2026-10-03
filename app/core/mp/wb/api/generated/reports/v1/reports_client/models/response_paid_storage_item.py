from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponsePaidStorageItem")


@_attrs_define
class ResponsePaidStorageItem:
    """
    Attributes:
        date (Union[Unset, str]): Calculation or recalculation date
        log_warehouse_coef (Union[Unset, float]): Logistics and storage coefficient
        office_id (Union[Unset, int]): Warehouse ID
        warehouse (Union[Unset, str]): Warehouse name
        warehouse_coef (Union[Unset, float]): Warehouse coefficient
        gi_id (Union[Unset, int]): Shipment ID
        chrt_id (Union[Unset, int]): Size ID
        size (Union[Unset, str]): Size (`techSize` in listing)
        barcode (Union[Unset, str]): Barcode
        subject (Union[Unset, str]): Subcategory
        brand (Union[Unset, str]): Brand
        vendor_code (Union[Unset, str]): Seller article number
        nm_id (Union[Unset, int]): Wildberries article number
        volume (Union[Unset, float]): Item volume
        calc_type (Union[Unset, str]): Calculation type
        warehouse_price (Union[Unset, float]): Storage price
        barcodes_count (Union[Unset, int]): Chargeable item units in the warehouse, in the last 24 hours
        pallet_place_code (Union[Unset, int]): Pallet place code
        pallet_count (Union[Unset, float]): Number of pallets
        original_date (Union[Unset, str]): Calculation date, in case of recalculation. If there was not a recalculation,
            the same as `date`
        loyalty_discount (Union[Unset, float]): Loyalty program discount, ₽
        tariff_fix_date (Union[Unset, str]): Tariff fixing date
        tariff_lower_date (Union[Unset, str]): Tariff reduction date
    """

    date: Union[Unset, str] = UNSET
    log_warehouse_coef: Union[Unset, float] = UNSET
    office_id: Union[Unset, int] = UNSET
    warehouse: Union[Unset, str] = UNSET
    warehouse_coef: Union[Unset, float] = UNSET
    gi_id: Union[Unset, int] = UNSET
    chrt_id: Union[Unset, int] = UNSET
    size: Union[Unset, str] = UNSET
    barcode: Union[Unset, str] = UNSET
    subject: Union[Unset, str] = UNSET
    brand: Union[Unset, str] = UNSET
    vendor_code: Union[Unset, str] = UNSET
    nm_id: Union[Unset, int] = UNSET
    volume: Union[Unset, float] = UNSET
    calc_type: Union[Unset, str] = UNSET
    warehouse_price: Union[Unset, float] = UNSET
    barcodes_count: Union[Unset, int] = UNSET
    pallet_place_code: Union[Unset, int] = UNSET
    pallet_count: Union[Unset, float] = UNSET
    original_date: Union[Unset, str] = UNSET
    loyalty_discount: Union[Unset, float] = UNSET
    tariff_fix_date: Union[Unset, str] = UNSET
    tariff_lower_date: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        date = self.date

        log_warehouse_coef = self.log_warehouse_coef

        office_id = self.office_id

        warehouse = self.warehouse

        warehouse_coef = self.warehouse_coef

        gi_id = self.gi_id

        chrt_id = self.chrt_id

        size = self.size

        barcode = self.barcode

        subject = self.subject

        brand = self.brand

        vendor_code = self.vendor_code

        nm_id = self.nm_id

        volume = self.volume

        calc_type = self.calc_type

        warehouse_price = self.warehouse_price

        barcodes_count = self.barcodes_count

        pallet_place_code = self.pallet_place_code

        pallet_count = self.pallet_count

        original_date = self.original_date

        loyalty_discount = self.loyalty_discount

        tariff_fix_date = self.tariff_fix_date

        tariff_lower_date = self.tariff_lower_date

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if date is not UNSET:
            field_dict["date"] = date
        if log_warehouse_coef is not UNSET:
            field_dict["logWarehouseCoef"] = log_warehouse_coef
        if office_id is not UNSET:
            field_dict["officeId"] = office_id
        if warehouse is not UNSET:
            field_dict["warehouse"] = warehouse
        if warehouse_coef is not UNSET:
            field_dict["warehouseCoef"] = warehouse_coef
        if gi_id is not UNSET:
            field_dict["giId"] = gi_id
        if chrt_id is not UNSET:
            field_dict["chrtId"] = chrt_id
        if size is not UNSET:
            field_dict["size"] = size
        if barcode is not UNSET:
            field_dict["barcode"] = barcode
        if subject is not UNSET:
            field_dict["subject"] = subject
        if brand is not UNSET:
            field_dict["brand"] = brand
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if volume is not UNSET:
            field_dict["volume"] = volume
        if calc_type is not UNSET:
            field_dict["calcType"] = calc_type
        if warehouse_price is not UNSET:
            field_dict["warehousePrice"] = warehouse_price
        if barcodes_count is not UNSET:
            field_dict["barcodesCount"] = barcodes_count
        if pallet_place_code is not UNSET:
            field_dict["palletPlaceCode"] = pallet_place_code
        if pallet_count is not UNSET:
            field_dict["palletCount"] = pallet_count
        if original_date is not UNSET:
            field_dict["originalDate"] = original_date
        if loyalty_discount is not UNSET:
            field_dict["loyaltyDiscount"] = loyalty_discount
        if tariff_fix_date is not UNSET:
            field_dict["tariffFixDate"] = tariff_fix_date
        if tariff_lower_date is not UNSET:
            field_dict["tariffLowerDate"] = tariff_lower_date

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        date = d.pop("date", UNSET)

        log_warehouse_coef = d.pop("logWarehouseCoef", UNSET)

        office_id = d.pop("officeId", UNSET)

        warehouse = d.pop("warehouse", UNSET)

        warehouse_coef = d.pop("warehouseCoef", UNSET)

        gi_id = d.pop("giId", UNSET)

        chrt_id = d.pop("chrtId", UNSET)

        size = d.pop("size", UNSET)

        barcode = d.pop("barcode", UNSET)

        subject = d.pop("subject", UNSET)

        brand = d.pop("brand", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        nm_id = d.pop("nmId", UNSET)

        volume = d.pop("volume", UNSET)

        calc_type = d.pop("calcType", UNSET)

        warehouse_price = d.pop("warehousePrice", UNSET)

        barcodes_count = d.pop("barcodesCount", UNSET)

        pallet_place_code = d.pop("palletPlaceCode", UNSET)

        pallet_count = d.pop("palletCount", UNSET)

        original_date = d.pop("originalDate", UNSET)

        loyalty_discount = d.pop("loyaltyDiscount", UNSET)

        tariff_fix_date = d.pop("tariffFixDate", UNSET)

        tariff_lower_date = d.pop("tariffLowerDate", UNSET)

        response_paid_storage_item = cls(
            date=date,
            log_warehouse_coef=log_warehouse_coef,
            office_id=office_id,
            warehouse=warehouse,
            warehouse_coef=warehouse_coef,
            gi_id=gi_id,
            chrt_id=chrt_id,
            size=size,
            barcode=barcode,
            subject=subject,
            brand=brand,
            vendor_code=vendor_code,
            nm_id=nm_id,
            volume=volume,
            calc_type=calc_type,
            warehouse_price=warehouse_price,
            barcodes_count=barcodes_count,
            pallet_place_code=pallet_place_code,
            pallet_count=pallet_count,
            original_date=original_date,
            loyalty_discount=loyalty_discount,
            tariff_fix_date=tariff_fix_date,
            tariff_lower_date=tariff_lower_date,
        )

        response_paid_storage_item.additional_properties = d
        return response_paid_storage_item

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
