from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.auction_advert_settings_payment_type import (
    AuctionAdvertSettingsPaymentType,
)

if TYPE_CHECKING:
    from ..models.auction_advert_settings_placements import (
        AuctionAdvertSettingsPlacements,
    )


T = TypeVar("T", bound="AuctionAdvertSettings")


@_attrs_define
class AuctionAdvertSettings:
    """Nastrojki kampanii

    Attributes:
        payment_type (AuctionAdvertSettingsPaymentType): <dl>
            <dt>Tip oplaty:</dt>
            <dd><code>cpm</code> — za pokazy</dd>
            <dd><code>cpc</code> — za klik</dd>
            </dl>
        name (str): Imja kampanii
        placements (AuctionAdvertSettingsPlacements): Mesta razmeschenija
    """

    payment_type: AuctionAdvertSettingsPaymentType
    name: str
    placements: "AuctionAdvertSettingsPlacements"
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
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.auction_advert_settings_placements import (
            AuctionAdvertSettingsPlacements,
        )

        d = dict(src_dict)
        payment_type = AuctionAdvertSettingsPaymentType(d.pop("payment_type"))

        name = d.pop("name")

        placements = AuctionAdvertSettingsPlacements.from_dict(d.pop("placements"))

        auction_advert_settings = cls(
            payment_type=payment_type,
            name=name,
            placements=placements,
        )

        auction_advert_settings.additional_properties = d
        return auction_advert_settings

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
