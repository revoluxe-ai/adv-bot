from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.advert_settings_payment_type import AdvertSettingsPaymentType

if TYPE_CHECKING:
    from ..models.advert_settings_placements import AdvertSettingsPlacements


T = TypeVar("T", bound="AdvertSettings")


@_attrs_define
class AdvertSettings:
    """Nastrojki kampanii

    Attributes:
        payment_type (AdvertSettingsPaymentType): Tip oplaty:
            - `cpm` — za pokazy
            - `cpc` — za klik
        name (str): Nazvanie kampanii
        placements (AdvertSettingsPlacements): Mesta razmeschenija
    """

    payment_type: AdvertSettingsPaymentType
    name: str
    placements: AdvertSettingsPlacements
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payment_type = self.payment_type.value

        name = self.name

        placements = self.placements.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "payment_type": payment_type,
                "name": name,
                "placements": placements,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any] | None) -> T:
        from ..models.advert_settings_placements import AdvertSettingsPlacements

        d = dict(src_dict or {})
        payment_type_raw = d.pop("payment_type", None)
        payment_type = AdvertSettingsPaymentType(payment_type_raw or "cpm")

        name = d.pop("name", None) or ""

        placements_raw = d.pop("placements", None)
        placements = AdvertSettingsPlacements.from_dict(
            placements_raw
            if placements_raw is not None
            else {"search": False, "recommendations": False}
        )

        advert_settings = cls(
            payment_type=payment_type,
            name=name,
            placements=placements,
        )

        advert_settings.additional_properties = d
        return advert_settings

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
