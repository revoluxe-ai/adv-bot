from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_auction_adverts_status import GetAuctionAdvertsStatus

if TYPE_CHECKING:
    from ..models.auction_advert_n_ms_settings import AuctionAdvertNMsSettings
    from ..models.auction_advert_settings import AuctionAdvertSettings
    from ..models.timestamps import Timestamps


T = TypeVar("T", bound="GetAuctionAdverts")


@_attrs_define
class GetAuctionAdverts:
    """
    Attributes:
        id (int): ID kampanii
        nm_settings (list['AuctionAdvertNMsSettings']): Nastrojki tovarov
        settings (AuctionAdvertSettings): Nastrojki kampanii
        status (GetAuctionAdvertsStatus): <dl>
            <dt>Status kampanii:</dt>
            <dd><code>-1</code> — udalena, protsess udalenija budet zavershen v techenie 10 minut</dd>
            <dd><code>4</code> — gotova k zapusku </dd>
            <dd><code>7</code> — zavershena</dd>
            <dd><code>8</code> — otmenena</dd>
            <dd><code>9</code> — aktivna</dd>
            <dd><code>11</code> — na pauze</dd>
            </dl>
        timestamps (Timestamps): Vremennye otmetki
    """

    id: int
    nm_settings: list["AuctionAdvertNMsSettings"]
    settings: "AuctionAdvertSettings"
    status: GetAuctionAdvertsStatus
    timestamps: "Timestamps"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        nm_settings = []
        for nm_settings_item_data in self.nm_settings:
            nm_settings_item = nm_settings_item_data.to_dict()
            nm_settings.append(nm_settings_item)

        settings = self.settings.to_dict()

        status = self.status.value

        timestamps = self.timestamps.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "nm_settings": nm_settings,
                "settings": settings,
                "status": status,
                "timestamps": timestamps,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.auction_advert_n_ms_settings import AuctionAdvertNMsSettings
        from ..models.auction_advert_settings import AuctionAdvertSettings
        from ..models.timestamps import Timestamps

        d = dict(src_dict)
        id = d.pop("id")

        nm_settings = []
        _nm_settings = d.pop("nm_settings")
        for nm_settings_item_data in _nm_settings:
            nm_settings_item = AuctionAdvertNMsSettings.from_dict(nm_settings_item_data)

            nm_settings.append(nm_settings_item)

        settings = AuctionAdvertSettings.from_dict(d.pop("settings"))

        status = GetAuctionAdvertsStatus(d.pop("status"))

        timestamps = Timestamps.from_dict(d.pop("timestamps"))

        get_auction_adverts = cls(
            id=id,
            nm_settings=nm_settings,
            settings=settings,
            status=status,
            timestamps=timestamps,
        )

        get_auction_adverts.additional_properties = d
        return get_auction_adverts

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
