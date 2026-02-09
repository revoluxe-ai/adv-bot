from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.warehouse_cargo_type import WarehouseCargoType
from ..models.warehouse_delivery_type import WarehouseDeliveryType
from ..types import UNSET, Unset

T = TypeVar("T", bound="Warehouse")


@_attrs_define
class Warehouse:
    """Dannye o sklade prodavtsa

    Attributes:
        name (str | Unset): Nazvanie sklada prodavtsa Example: ul. Troitskaja, Podol'sk, Moskovskaja obl..
        office_id (int | Unset): ID sklada WB Example: 15.
        id (int | Unset): ID sklada prodavtsa Example: 1.
        cargo_type (WarehouseCargoType | Unset): Tip tovara:
              - `1` — malogabaritnyj tovar (MGT)
              - `2` — sverhgabaritnyj tovar (SGT)
              - `3` — krupnogabaritnyj tovar (KGT+)
             Example: 1.
        delivery_type (WarehouseDeliveryType | Unset): Tip dostavki, kotoryj prinimaet sklad:
              - `1` — dostavka na sklad WB (FBS)
              - `2` — dostavka silami prodavtsa (DBS)
              - `3` — dostavka kur'erom WB (DBW)
              - `5` — samovyvoz (C&C)
              - `6` — ekspress-dostavka silami prodavtsa (EDBS)
             Example: 1.
        is_deleting (bool | Unset): Sklad udaljaetsja:
              - `false` — net
              - `true` — da

            Posle udalenija sklad propadet iz spiska
        is_processing (bool | Unset): Dannye sklada obnovljajutsja:
              - `false` — net
              - `true` — da, obnovlenie i udalenie ostatkov nedostupno

            Obnovlenie dannyh mozhet zanimat' neskol'ko minut
             Example: True.
    """

    name: str | Unset = UNSET
    office_id: int | Unset = UNSET
    id: int | Unset = UNSET
    cargo_type: WarehouseCargoType | Unset = UNSET
    delivery_type: WarehouseDeliveryType | Unset = UNSET
    is_deleting: bool | Unset = UNSET
    is_processing: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        office_id = self.office_id

        id = self.id

        cargo_type: int | Unset = UNSET
        if not isinstance(self.cargo_type, Unset):
            cargo_type = self.cargo_type.value

        delivery_type: int | Unset = UNSET
        if not isinstance(self.delivery_type, Unset):
            delivery_type = self.delivery_type.value

        is_deleting = self.is_deleting

        is_processing = self.is_processing

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if office_id is not UNSET:
            field_dict["officeId"] = office_id
        if id is not UNSET:
            field_dict["id"] = id
        if cargo_type is not UNSET:
            field_dict["cargoType"] = cargo_type
        if delivery_type is not UNSET:
            field_dict["deliveryType"] = delivery_type
        if is_deleting is not UNSET:
            field_dict["isDeleting"] = is_deleting
        if is_processing is not UNSET:
            field_dict["isProcessing"] = is_processing

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name", UNSET)

        office_id = d.pop("officeId", UNSET)

        id = d.pop("id", UNSET)

        _cargo_type = d.pop("cargoType", UNSET)
        cargo_type: WarehouseCargoType | Unset
        if isinstance(_cargo_type, Unset):
            cargo_type = UNSET
        else:
            cargo_type = WarehouseCargoType(_cargo_type)

        _delivery_type = d.pop("deliveryType", UNSET)
        delivery_type: WarehouseDeliveryType | Unset
        if isinstance(_delivery_type, Unset):
            delivery_type = UNSET
        else:
            delivery_type = WarehouseDeliveryType(_delivery_type)

        is_deleting = d.pop("isDeleting", UNSET)

        is_processing = d.pop("isProcessing", UNSET)

        warehouse = cls(
            name=name,
            office_id=office_id,
            id=id,
            cargo_type=cargo_type,
            delivery_type=delivery_type,
            is_deleting=is_deleting,
            is_processing=is_processing,
        )

        warehouse.additional_properties = d
        return warehouse

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
