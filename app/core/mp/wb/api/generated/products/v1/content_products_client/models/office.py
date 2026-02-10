from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.office_cargo_type import OfficeCargoType
from ..models.office_delivery_type import OfficeDeliveryType
from ..types import UNSET, Unset

T = TypeVar("T", bound="Office")


@_attrs_define
class Office:
    """Dannye o sklade WB

    Attributes:
        address (str | Unset): Adres Example: ul. Troitskaja, Podol'sk, Moskovskaja obl..
        name (str | Unset): Nazvanie Example: Koledino.
        city (str | Unset): Gorod Example: Moskva.
        id (int | Unset): ID Example: 15.
        longitude (float | Unset): Dolgota Example: 55.386871.
        latitude (float | Unset): Shirota Example: 37.588898.
        cargo_type (OfficeCargoType | Unset): Tip tovara, kotoryj prinimaet sklad:
              - `1` — malogabaritnyj tovar (MGT)
              - `2` — sverhgabaritnyj tovar (SGT)
              - `3` — krupnogabaritnyj tovar (KGT+)
             Example: 1.
        delivery_type (OfficeDeliveryType | Unset): Tip dostavki, kotoryj prinimaet sklad:
              - `1` — dostavka na sklad WB (FBS)
              - `2` — dostavka silami prodavtsa (DBS)
              - `3` — dostavka kur'erom WB (DBW)
              - `5` — samovyvoz (C&C)
              - `6` — ekspress-dostavka silami prodavtsa (EDBS)
             Example: 1.
        federal_district (None | str | Unset): Federal'nyj okrug sklada WB. Esli `null`, sklad nahoditsja za predelami
            RF ili federal'nyj okrug ne ukazan Example: Tsentral'nyj.
        selected (bool | Unset): Priznak togo, chto sklad uzhe vybran prodavtsom
    """

    address: str | Unset = UNSET
    name: str | Unset = UNSET
    city: str | Unset = UNSET
    id: int | Unset = UNSET
    longitude: float | Unset = UNSET
    latitude: float | Unset = UNSET
    cargo_type: OfficeCargoType | Unset = UNSET
    delivery_type: OfficeDeliveryType | Unset = UNSET
    federal_district: None | str | Unset = UNSET
    selected: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        address = self.address

        name = self.name

        city = self.city

        id = self.id

        longitude = self.longitude

        latitude = self.latitude

        cargo_type: int | Unset = UNSET
        if not isinstance(self.cargo_type, Unset):
            cargo_type = self.cargo_type.value

        delivery_type: int | Unset = UNSET
        if not isinstance(self.delivery_type, Unset):
            delivery_type = self.delivery_type.value

        federal_district: None | str | Unset
        if isinstance(self.federal_district, Unset):
            federal_district = UNSET
        else:
            federal_district = self.federal_district

        selected = self.selected

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if address is not UNSET:
            field_dict["address"] = address
        if name is not UNSET:
            field_dict["name"] = name
        if city is not UNSET:
            field_dict["city"] = city
        if id is not UNSET:
            field_dict["id"] = id
        if longitude is not UNSET:
            field_dict["longitude"] = longitude
        if latitude is not UNSET:
            field_dict["latitude"] = latitude
        if cargo_type is not UNSET:
            field_dict["cargoType"] = cargo_type
        if delivery_type is not UNSET:
            field_dict["deliveryType"] = delivery_type
        if federal_district is not UNSET:
            field_dict["federalDistrict"] = federal_district
        if selected is not UNSET:
            field_dict["selected"] = selected

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        address = d.pop("address", UNSET)

        name = d.pop("name", UNSET)

        city = d.pop("city", UNSET)

        id = d.pop("id", UNSET)

        longitude = d.pop("longitude", UNSET)

        latitude = d.pop("latitude", UNSET)

        _cargo_type = d.pop("cargoType", UNSET)
        cargo_type: OfficeCargoType | Unset
        if isinstance(_cargo_type, Unset):
            cargo_type = UNSET
        else:
            cargo_type = OfficeCargoType(_cargo_type)

        _delivery_type = d.pop("deliveryType", UNSET)
        delivery_type: OfficeDeliveryType | Unset
        if isinstance(_delivery_type, Unset):
            delivery_type = UNSET
        else:
            delivery_type = OfficeDeliveryType(_delivery_type)

        def _parse_federal_district(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        federal_district = _parse_federal_district(d.pop("federalDistrict", UNSET))

        selected = d.pop("selected", UNSET)

        office = cls(
            address=address,
            name=name,
            city=city,
            id=id,
            longitude=longitude,
            latitude=latitude,
            cargo_type=cargo_type,
            delivery_type=delivery_type,
            federal_district=federal_district,
            selected=selected,
        )

        office.additional_properties = d
        return office

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
