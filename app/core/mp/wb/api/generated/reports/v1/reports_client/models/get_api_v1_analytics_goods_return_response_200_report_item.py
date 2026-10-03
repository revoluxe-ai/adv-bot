import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.get_api_v1_analytics_goods_return_response_200_report_item_is_status_active import (
    GetApiV1AnalyticsGoodsReturnResponse200ReportItemIsStatusActive,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="GetApiV1AnalyticsGoodsReturnResponse200ReportItem")


@_attrs_define
class GetApiV1AnalyticsGoodsReturnResponse200ReportItem:
    """
    Attributes:
        barcode (Union[Unset, str]): Barcode Example: 1680063403480.
        brand (Union[Unset, str]): Brand Example: dub.
        completed_dt (Union[None, Unset, str]): Date and time the seller received return Example: 2025-03-31T11:33:53.
        dst_office_address (Union[Unset, str]): Address of POP where the seller receives returns Example: Жуковский
            Улица Маяковского 19.
        dst_office_id (Union[Unset, int]): ID of POP where the seller receives returns Example: 310105.
        expired_dt (Union[None, Unset, str]): Expiration date and time of the storage period Example:
            2025-03-31T11:33:53.
        is_status_active (Union[Unset, GetApiV1AnalyticsGoodsReturnResponse200ReportItemIsStatusActive]): Type of return
            status:

              * `0` — archive
              * `1` — active
        nm_id (Union[Unset, int]): WB item number Example: 12862181.
        order_dt (Union[Unset, datetime.date]): Date of the return order Example: 2024-08-26.
        order_id (Union[Unset, int]): Assembly order number Example: 2034240826.
        ready_to_return_dt (Union[None, Unset, str]): Date and time when the return is ready for delivery Example:
            2025-01-31T08:33:50.
        reason (Union[Unset, str]): The reason for the return Example: Цвет.
        return_type (Union[Unset, str]): Return type Example: Возврат заблокированного товара.
        shk_id (Union[Unset, int]): SKU of the item unit Example: 23411783472.
        srid (Union[Unset, str]): The unique ID of the return order Example: ad3817664d3046c5a8d55054d8be96d6.
        status (Union[Unset, str]): Return status Example: В пути в пвз.
        sticker_id (Union[Unset, str]): Sticker of the return order Example: 33811984302.
        subject_name (Union[Unset, str]): Subcategory name Example: Багажные бирки.
        tech_size (Union[Unset, str]): Size Example: 0.
    """

    barcode: Union[Unset, str] = UNSET
    brand: Union[Unset, str] = UNSET
    completed_dt: Union[None, Unset, str] = UNSET
    dst_office_address: Union[Unset, str] = UNSET
    dst_office_id: Union[Unset, int] = UNSET
    expired_dt: Union[None, Unset, str] = UNSET
    is_status_active: Union[
        Unset, GetApiV1AnalyticsGoodsReturnResponse200ReportItemIsStatusActive
    ] = UNSET
    nm_id: Union[Unset, int] = UNSET
    order_dt: Union[Unset, datetime.date] = UNSET
    order_id: Union[Unset, int] = UNSET
    ready_to_return_dt: Union[None, Unset, str] = UNSET
    reason: Union[Unset, str] = UNSET
    return_type: Union[Unset, str] = UNSET
    shk_id: Union[Unset, int] = UNSET
    srid: Union[Unset, str] = UNSET
    status: Union[Unset, str] = UNSET
    sticker_id: Union[Unset, str] = UNSET
    subject_name: Union[Unset, str] = UNSET
    tech_size: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        barcode = self.barcode

        brand = self.brand

        completed_dt: Union[None, Unset, str]
        if isinstance(self.completed_dt, Unset):
            completed_dt = UNSET
        else:
            completed_dt = self.completed_dt

        dst_office_address = self.dst_office_address

        dst_office_id = self.dst_office_id

        expired_dt: Union[None, Unset, str]
        if isinstance(self.expired_dt, Unset):
            expired_dt = UNSET
        else:
            expired_dt = self.expired_dt

        is_status_active: Union[Unset, int] = UNSET
        if not isinstance(self.is_status_active, Unset):
            is_status_active = self.is_status_active.value

        nm_id = self.nm_id

        order_dt: Union[Unset, str] = UNSET
        if not isinstance(self.order_dt, Unset):
            order_dt = self.order_dt.isoformat()

        order_id = self.order_id

        ready_to_return_dt: Union[None, Unset, str]
        if isinstance(self.ready_to_return_dt, Unset):
            ready_to_return_dt = UNSET
        else:
            ready_to_return_dt = self.ready_to_return_dt

        reason = self.reason

        return_type = self.return_type

        shk_id = self.shk_id

        srid = self.srid

        status = self.status

        sticker_id = self.sticker_id

        subject_name = self.subject_name

        tech_size = self.tech_size

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if barcode is not UNSET:
            field_dict["barcode"] = barcode
        if brand is not UNSET:
            field_dict["brand"] = brand
        if completed_dt is not UNSET:
            field_dict["completedDt"] = completed_dt
        if dst_office_address is not UNSET:
            field_dict["dstOfficeAddress"] = dst_office_address
        if dst_office_id is not UNSET:
            field_dict["dstOfficeId"] = dst_office_id
        if expired_dt is not UNSET:
            field_dict["expiredDt"] = expired_dt
        if is_status_active is not UNSET:
            field_dict["isStatusActive"] = is_status_active
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if order_dt is not UNSET:
            field_dict["orderDt"] = order_dt
        if order_id is not UNSET:
            field_dict["orderId"] = order_id
        if ready_to_return_dt is not UNSET:
            field_dict["readyToReturnDt"] = ready_to_return_dt
        if reason is not UNSET:
            field_dict["reason"] = reason
        if return_type is not UNSET:
            field_dict["returnType"] = return_type
        if shk_id is not UNSET:
            field_dict["shkId"] = shk_id
        if srid is not UNSET:
            field_dict["srid"] = srid
        if status is not UNSET:
            field_dict["status"] = status
        if sticker_id is not UNSET:
            field_dict["stickerId"] = sticker_id
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if tech_size is not UNSET:
            field_dict["techSize"] = tech_size

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        barcode = d.pop("barcode", UNSET)

        brand = d.pop("brand", UNSET)

        def _parse_completed_dt(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        completed_dt = _parse_completed_dt(d.pop("completedDt", UNSET))

        dst_office_address = d.pop("dstOfficeAddress", UNSET)

        dst_office_id = d.pop("dstOfficeId", UNSET)

        def _parse_expired_dt(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        expired_dt = _parse_expired_dt(d.pop("expiredDt", UNSET))

        _is_status_active = d.pop("isStatusActive", UNSET)
        is_status_active: Union[
            Unset, GetApiV1AnalyticsGoodsReturnResponse200ReportItemIsStatusActive
        ]
        if isinstance(_is_status_active, Unset):
            is_status_active = UNSET
        else:
            is_status_active = (
                GetApiV1AnalyticsGoodsReturnResponse200ReportItemIsStatusActive(
                    _is_status_active
                )
            )

        nm_id = d.pop("nmId", UNSET)

        _order_dt = d.pop("orderDt", UNSET)
        order_dt: Union[Unset, datetime.date]
        if isinstance(_order_dt, Unset):
            order_dt = UNSET
        else:
            order_dt = isoparse(_order_dt).date()

        order_id = d.pop("orderId", UNSET)

        def _parse_ready_to_return_dt(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        ready_to_return_dt = _parse_ready_to_return_dt(d.pop("readyToReturnDt", UNSET))

        reason = d.pop("reason", UNSET)

        return_type = d.pop("returnType", UNSET)

        shk_id = d.pop("shkId", UNSET)

        srid = d.pop("srid", UNSET)

        status = d.pop("status", UNSET)

        sticker_id = d.pop("stickerId", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        tech_size = d.pop("techSize", UNSET)

        get_api_v1_analytics_goods_return_response_200_report_item = cls(
            barcode=barcode,
            brand=brand,
            completed_dt=completed_dt,
            dst_office_address=dst_office_address,
            dst_office_id=dst_office_id,
            expired_dt=expired_dt,
            is_status_active=is_status_active,
            nm_id=nm_id,
            order_dt=order_dt,
            order_id=order_id,
            ready_to_return_dt=ready_to_return_dt,
            reason=reason,
            return_type=return_type,
            shk_id=shk_id,
            srid=srid,
            status=status,
            sticker_id=sticker_id,
            subject_name=subject_name,
            tech_size=tech_size,
        )

        get_api_v1_analytics_goods_return_response_200_report_item.additional_properties = d
        return get_api_v1_analytics_goods_return_response_200_report_item

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
