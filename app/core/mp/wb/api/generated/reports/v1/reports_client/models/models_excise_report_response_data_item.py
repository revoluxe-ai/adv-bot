from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ModelsExciseReportResponseDataItem")


@_attrs_define
class ModelsExciseReportResponseDataItem:
    """
    Attributes:
        name (Union[Unset, str]): Buyer's country Example: Россия.
        price (Union[Unset, float]): Price including VAT Example: 100.
        currency_name_short (Union[Unset, str]): Currency Example: AMD.
        excise_short (Union[Unset, str]): Labeling code Example: 0102900254680370215_Re/=lSbNiGD.
        barcode (Union[Unset, str]): Barcode Example: 2038893425820.
        nm_id (Union[Unset, int]): Wildberries article number Example: 169085355.
        operation_type_id (Union[Unset, int]): Operation type, if exists:

              * `1` — withdraw from circulation
              * `2` — return to sale
             Example: 1.
        fiscal_doc_number (Union[Unset, int]): Receipt number, if exists Example: 12345678.
        fiscal_dt (Union[Unset, str]): Date in the receipt, if exists, YYYY-MM-DD Example: 2024-01-01.
        fiscal_drive_number (Union[Unset, str]): Fiscal storage number, if exists
        rid (Union[Unset, int]): `Rid`
             Example: 606217433440.
        srid (Union[Unset, str]): `Srid`
             Example: 7513432034713632943.1.0.
    """

    name: Union[Unset, str] = UNSET
    price: Union[Unset, float] = UNSET
    currency_name_short: Union[Unset, str] = UNSET
    excise_short: Union[Unset, str] = UNSET
    barcode: Union[Unset, str] = UNSET
    nm_id: Union[Unset, int] = UNSET
    operation_type_id: Union[Unset, int] = UNSET
    fiscal_doc_number: Union[Unset, int] = UNSET
    fiscal_dt: Union[Unset, str] = UNSET
    fiscal_drive_number: Union[Unset, str] = UNSET
    rid: Union[Unset, int] = UNSET
    srid: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        price = self.price

        currency_name_short = self.currency_name_short

        excise_short = self.excise_short

        barcode = self.barcode

        nm_id = self.nm_id

        operation_type_id = self.operation_type_id

        fiscal_doc_number = self.fiscal_doc_number

        fiscal_dt = self.fiscal_dt

        fiscal_drive_number = self.fiscal_drive_number

        rid = self.rid

        srid = self.srid

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if price is not UNSET:
            field_dict["price"] = price
        if currency_name_short is not UNSET:
            field_dict["currency_name_short"] = currency_name_short
        if excise_short is not UNSET:
            field_dict["excise_short"] = excise_short
        if barcode is not UNSET:
            field_dict["barcode"] = barcode
        if nm_id is not UNSET:
            field_dict["nm_id"] = nm_id
        if operation_type_id is not UNSET:
            field_dict["operation_type_id"] = operation_type_id
        if fiscal_doc_number is not UNSET:
            field_dict["fiscal_doc_number"] = fiscal_doc_number
        if fiscal_dt is not UNSET:
            field_dict["fiscal_dt"] = fiscal_dt
        if fiscal_drive_number is not UNSET:
            field_dict["fiscal_drive_number"] = fiscal_drive_number
        if rid is not UNSET:
            field_dict["rid"] = rid
        if srid is not UNSET:
            field_dict["srid"] = srid

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name", UNSET)

        price = d.pop("price", UNSET)

        currency_name_short = d.pop("currency_name_short", UNSET)

        excise_short = d.pop("excise_short", UNSET)

        barcode = d.pop("barcode", UNSET)

        nm_id = d.pop("nm_id", UNSET)

        operation_type_id = d.pop("operation_type_id", UNSET)

        fiscal_doc_number = d.pop("fiscal_doc_number", UNSET)

        fiscal_dt = d.pop("fiscal_dt", UNSET)

        fiscal_drive_number = d.pop("fiscal_drive_number", UNSET)

        rid = d.pop("rid", UNSET)

        srid = d.pop("srid", UNSET)

        models_excise_report_response_data_item = cls(
            name=name,
            price=price,
            currency_name_short=currency_name_short,
            excise_short=excise_short,
            barcode=barcode,
            nm_id=nm_id,
            operation_type_id=operation_type_id,
            fiscal_doc_number=fiscal_doc_number,
            fiscal_dt=fiscal_dt,
            fiscal_drive_number=fiscal_drive_number,
            rid=rid,
            srid=srid,
        )

        models_excise_report_response_data_item.additional_properties = d
        return models_excise_report_response_data_item

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
