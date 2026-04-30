from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.advert_settings_payment_type import AdvertSettingsPaymentType

if TYPE_CHECKING:
    from ..models.advert_settings_placements import AdvertSettingsPlacements


T = TypeVar("T", bound="AdvertSettings")


@_attrs_define
class AdvertSettings:
    """Campaign settings

    Attributes:
        payment_type (AdvertSettingsPaymentType): Payment type:
            - `cpm` — cost per mille
            - `cpc` — cost per click
        name (str): Campaign name
        placements (AdvertSettingsPlacements): Placements
    """

    payment_type: AdvertSettingsPaymentType
    name: str
    placements: "AdvertSettingsPlacements"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payment_type = self.payment_type.value

        name = self.name

        placements = self.placements.to_dict()

        field_dict: Dict[str, Any] = {}
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
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.advert_settings_placements import AdvertSettingsPlacements

        d = src_dict.copy()
        payment_type = AdvertSettingsPaymentType(d.pop("payment_type"))

        name = d.pop("name")

        placements = AdvertSettingsPlacements.from_dict(d.pop("placements"))

        advert_settings = cls(
            payment_type=payment_type,
            name=name,
            placements=placements,
        )

        advert_settings.additional_properties = d
        return advert_settings

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
