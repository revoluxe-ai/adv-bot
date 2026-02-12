from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="SupplierTaskMetadataType0")


@_attrs_define
class SupplierTaskMetadataType0:
    """Dannye otveta

    Attributes:
        upload_id (int | Unset): ID zagruzki Example: 395643565.
        status (int | Unset): Status zagruzki:
              * `3` — obrabotana, v tovarah net oshibok, tseny i skidki obnovilis'
              * `4` — otmenena
              * `5` — obrabotana, no v tovarah est' oshibki. Dlja tovarov bez oshibok tseny i skidki obnovilis', a oshibki
            v ostal'nyh tovarah mozhno poluchit' s pomosch'ju metoda [Detalizatsija obrabotannoj zagruzki](./work-with-
            products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1goods~1task/get)
              * `6` — obrabotana, no vo vseh tovarah est' oshibki. Ih tozhe mozhno poluchit' s pomosch'ju metoda
            [Detalizatsija obrabotannoj zagruzki](./work-with-products#tag/Ceny-i-
            skidki/paths/~1api~1v2~1history~1goods~1task/get)
             Example: 3.
        upload_date (datetime.datetime | Unset): Data i vremja, kogda zagruzka sozdana Example:
            2022-08-21T22:00:13+02:00.
        activation_date (datetime.datetime | Unset): Data i vremja, kogda zagruzka otpravljaetsja v obrabotku Example:
            2022-08-21T22:00:13+02:00.
        over_all_goods_number (int | Unset): Vsego tovarov
        success_goods_number (int | Unset): Tovarov bez oshibok
    """

    upload_id: int | Unset = UNSET
    status: int | Unset = UNSET
    upload_date: datetime.datetime | Unset = UNSET
    activation_date: datetime.datetime | Unset = UNSET
    over_all_goods_number: int | Unset = UNSET
    success_goods_number: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        upload_id = self.upload_id

        status = self.status

        upload_date: str | Unset = UNSET
        if not isinstance(self.upload_date, Unset):
            upload_date = self.upload_date.isoformat()

        activation_date: str | Unset = UNSET
        if not isinstance(self.activation_date, Unset):
            activation_date = self.activation_date.isoformat()

        over_all_goods_number = self.over_all_goods_number

        success_goods_number = self.success_goods_number

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if upload_id is not UNSET:
            field_dict["uploadID"] = upload_id
        if status is not UNSET:
            field_dict["status"] = status
        if upload_date is not UNSET:
            field_dict["uploadDate"] = upload_date
        if activation_date is not UNSET:
            field_dict["activationDate"] = activation_date
        if over_all_goods_number is not UNSET:
            field_dict["overAllGoodsNumber"] = over_all_goods_number
        if success_goods_number is not UNSET:
            field_dict["successGoodsNumber"] = success_goods_number

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        upload_id = d.pop("uploadID", UNSET)

        status = d.pop("status", UNSET)

        _upload_date = d.pop("uploadDate", UNSET)
        upload_date: datetime.datetime | Unset
        if isinstance(_upload_date, Unset):
            upload_date = UNSET
        else:
            upload_date = isoparse(_upload_date)

        _activation_date = d.pop("activationDate", UNSET)
        activation_date: datetime.datetime | Unset
        if isinstance(_activation_date, Unset):
            activation_date = UNSET
        else:
            activation_date = isoparse(_activation_date)

        over_all_goods_number = d.pop("overAllGoodsNumber", UNSET)

        success_goods_number = d.pop("successGoodsNumber", UNSET)

        supplier_task_metadata_type_0 = cls(
            upload_id=upload_id,
            status=status,
            upload_date=upload_date,
            activation_date=activation_date,
            over_all_goods_number=over_all_goods_number,
            success_goods_number=success_goods_number,
        )

        supplier_task_metadata_type_0.additional_properties = d
        return supplier_task_metadata_type_0

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
