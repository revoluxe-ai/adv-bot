from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.orders_item_warehouse_type import OrdersItemWarehouseType
from ..types import UNSET, Unset

T = TypeVar("T", bound="OrdersItem")


@_attrs_define
class OrdersItem:
    """
    Attributes:
        date (Union[Unset, str]): Date and time of order. This field equals to `dateFrom` in request if `flag=1`. If the
            time zone is not specified, then Moscow time UTC+3 is taken.
        last_change_date (Union[Unset, str]): Date and time of refreshing info of service. This field corresponds to the
            `dateFrom` parameter in the request if the `flag=0` parameter exist or not specified. If the time zone is not
            specified, then Moscow time UTC+3 is taken.
        warehouse_name (Union[Unset, str]): Shipping warehouse name
        warehouse_type (Union[Unset, OrdersItemWarehouseType]): Type of items storage warehouse:
              - `Склад WB` —  WB warehouse
              - `Склад продавца` — seller warehouse
        country_name (Union[Unset, str]): Country
        oblast_okrug_name (Union[Unset, str]): Area
        region_name (Union[Unset, str]): Region
        supplier_article (Union[Unset, str]): Seller article number
        nm_id (Union[Unset, int]): WB article number
        barcode (Union[Unset, str]): Barcode
        category (Union[Unset, str]): Category
        subject (Union[Unset, str]): Subcategory
        brand (Union[Unset, str]): Brand
        tech_size (Union[Unset, str]): Item size
        income_id (Union[Unset, int]): Supply number
        is_supply (Union[Unset, bool]): Supply contract
        is_realization (Union[Unset, bool]): Implementation contract
        total_price (Union[Unset, float]): Price without discounts
        discount_percent (Union[Unset, int]): Seller discount, %
        spp (Union[Unset, float]): WB discount, %
        finished_price (Union[Unset, float]): Price with all discounts, except WB Wallet sum
        price_with_disc (Union[Unset, float]): Price with seller discount, including WB Club discount
        is_cancel (Union[Unset, bool]): Order cancel:
             - `true` — the order is cancelled
        cancel_date (Union[Unset, str]): Date and time for order canceling. If order wasn't canceled, then
            `"0001-01-01T00:00:00"`. If the time zone is not specified, then Moscow time UTC+3 is taken.
        sticker (Union[Unset, str]): sticker ID
        g_number (Union[Unset, str]): Buyer's cart ID. Orders within a single transaction will have the same `gNumber`
        srid (Union[Unset, str]): Unique order ID. <br> Note for those working with Marketplace API: `srid` equals `rid`
            in response of orders methods
    """

    date: Union[Unset, str] = UNSET
    last_change_date: Union[Unset, str] = UNSET
    warehouse_name: Union[Unset, str] = UNSET
    warehouse_type: Union[Unset, OrdersItemWarehouseType] = UNSET
    country_name: Union[Unset, str] = UNSET
    oblast_okrug_name: Union[Unset, str] = UNSET
    region_name: Union[Unset, str] = UNSET
    supplier_article: Union[Unset, str] = UNSET
    nm_id: Union[Unset, int] = UNSET
    barcode: Union[Unset, str] = UNSET
    category: Union[Unset, str] = UNSET
    subject: Union[Unset, str] = UNSET
    brand: Union[Unset, str] = UNSET
    tech_size: Union[Unset, str] = UNSET
    income_id: Union[Unset, int] = UNSET
    is_supply: Union[Unset, bool] = UNSET
    is_realization: Union[Unset, bool] = UNSET
    total_price: Union[Unset, float] = UNSET
    discount_percent: Union[Unset, int] = UNSET
    spp: Union[Unset, float] = UNSET
    finished_price: Union[Unset, float] = UNSET
    price_with_disc: Union[Unset, float] = UNSET
    is_cancel: Union[Unset, bool] = UNSET
    cancel_date: Union[Unset, str] = UNSET
    sticker: Union[Unset, str] = UNSET
    g_number: Union[Unset, str] = UNSET
    srid: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        date = self.date

        last_change_date = self.last_change_date

        warehouse_name = self.warehouse_name

        warehouse_type: Union[Unset, str] = UNSET
        if not isinstance(self.warehouse_type, Unset):
            warehouse_type = self.warehouse_type.value

        country_name = self.country_name

        oblast_okrug_name = self.oblast_okrug_name

        region_name = self.region_name

        supplier_article = self.supplier_article

        nm_id = self.nm_id

        barcode = self.barcode

        category = self.category

        subject = self.subject

        brand = self.brand

        tech_size = self.tech_size

        income_id = self.income_id

        is_supply = self.is_supply

        is_realization = self.is_realization

        total_price = self.total_price

        discount_percent = self.discount_percent

        spp = self.spp

        finished_price = self.finished_price

        price_with_disc = self.price_with_disc

        is_cancel = self.is_cancel

        cancel_date = self.cancel_date

        sticker = self.sticker

        g_number = self.g_number

        srid = self.srid

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if date is not UNSET:
            field_dict["date"] = date
        if last_change_date is not UNSET:
            field_dict["lastChangeDate"] = last_change_date
        if warehouse_name is not UNSET:
            field_dict["warehouseName"] = warehouse_name
        if warehouse_type is not UNSET:
            field_dict["warehouseType"] = warehouse_type
        if country_name is not UNSET:
            field_dict["countryName"] = country_name
        if oblast_okrug_name is not UNSET:
            field_dict["oblastOkrugName"] = oblast_okrug_name
        if region_name is not UNSET:
            field_dict["regionName"] = region_name
        if supplier_article is not UNSET:
            field_dict["supplierArticle"] = supplier_article
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if barcode is not UNSET:
            field_dict["barcode"] = barcode
        if category is not UNSET:
            field_dict["category"] = category
        if subject is not UNSET:
            field_dict["subject"] = subject
        if brand is not UNSET:
            field_dict["brand"] = brand
        if tech_size is not UNSET:
            field_dict["techSize"] = tech_size
        if income_id is not UNSET:
            field_dict["incomeID"] = income_id
        if is_supply is not UNSET:
            field_dict["isSupply"] = is_supply
        if is_realization is not UNSET:
            field_dict["isRealization"] = is_realization
        if total_price is not UNSET:
            field_dict["totalPrice"] = total_price
        if discount_percent is not UNSET:
            field_dict["discountPercent"] = discount_percent
        if spp is not UNSET:
            field_dict["spp"] = spp
        if finished_price is not UNSET:
            field_dict["finishedPrice"] = finished_price
        if price_with_disc is not UNSET:
            field_dict["priceWithDisc"] = price_with_disc
        if is_cancel is not UNSET:
            field_dict["isCancel"] = is_cancel
        if cancel_date is not UNSET:
            field_dict["cancelDate"] = cancel_date
        if sticker is not UNSET:
            field_dict["sticker"] = sticker
        if g_number is not UNSET:
            field_dict["gNumber"] = g_number
        if srid is not UNSET:
            field_dict["srid"] = srid

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        date = d.pop("date", UNSET)

        last_change_date = d.pop("lastChangeDate", UNSET)

        warehouse_name = d.pop("warehouseName", UNSET)

        _warehouse_type = d.pop("warehouseType", UNSET)
        warehouse_type: Union[Unset, OrdersItemWarehouseType]
        if isinstance(_warehouse_type, Unset):
            warehouse_type = UNSET
        else:
            warehouse_type = OrdersItemWarehouseType(_warehouse_type)

        country_name = d.pop("countryName", UNSET)

        oblast_okrug_name = d.pop("oblastOkrugName", UNSET)

        region_name = d.pop("regionName", UNSET)

        supplier_article = d.pop("supplierArticle", UNSET)

        nm_id = d.pop("nmId", UNSET)

        barcode = d.pop("barcode", UNSET)

        category = d.pop("category", UNSET)

        subject = d.pop("subject", UNSET)

        brand = d.pop("brand", UNSET)

        tech_size = d.pop("techSize", UNSET)

        income_id = d.pop("incomeID", UNSET)

        is_supply = d.pop("isSupply", UNSET)

        is_realization = d.pop("isRealization", UNSET)

        total_price = d.pop("totalPrice", UNSET)

        discount_percent = d.pop("discountPercent", UNSET)

        spp = d.pop("spp", UNSET)

        finished_price = d.pop("finishedPrice", UNSET)

        price_with_disc = d.pop("priceWithDisc", UNSET)

        is_cancel = d.pop("isCancel", UNSET)

        cancel_date = d.pop("cancelDate", UNSET)

        sticker = d.pop("sticker", UNSET)

        g_number = d.pop("gNumber", UNSET)

        srid = d.pop("srid", UNSET)

        orders_item = cls(
            date=date,
            last_change_date=last_change_date,
            warehouse_name=warehouse_name,
            warehouse_type=warehouse_type,
            country_name=country_name,
            oblast_okrug_name=oblast_okrug_name,
            region_name=region_name,
            supplier_article=supplier_article,
            nm_id=nm_id,
            barcode=barcode,
            category=category,
            subject=subject,
            brand=brand,
            tech_size=tech_size,
            income_id=income_id,
            is_supply=is_supply,
            is_realization=is_realization,
            total_price=total_price,
            discount_percent=discount_percent,
            spp=spp,
            finished_price=finished_price,
            price_with_disc=price_with_disc,
            is_cancel=is_cancel,
            cancel_date=cancel_date,
            sticker=sticker,
            g_number=g_number,
            srid=srid,
        )

        orders_item.additional_properties = d
        return orders_item

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
