from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_auction_adverts_adverts_item_status import GetAuctionAdvertsAdvertsItemStatus

if TYPE_CHECKING:
    from ..models.auction_advert_n_ms_settings import AuctionAdvertNMsSettings
    from ..models.auction_advert_settings import AuctionAdvertSettings
    from ..models.timestamps import Timestamps


T = TypeVar("T", bound="GetAuctionAdvertsAdvertsItem")


@_attrs_define
class GetAuctionAdvertsAdvertsItem:
    """
    Attributes:
        id (int): ID kampanii
        nm_settings (List['AuctionAdvertNMsSettings']): Nastrojki tovarov
        settings (AuctionAdvertSettings): Nastrojki kampanii
        status (GetAuctionAdvertsAdvertsItemStatus): Status kampanii:
            - `-1` — udalena, protsess udalenija budet zavershen v techenie 10 minut
            - `4` — gotova k zapusku
            - `7` — zavershena
            - `8` — otmenena
            - `9` — aktivna
            - `11` — na pauze
        timestamps (Timestamps): Vremennye otmetki
        bid_type (str): Tip stavki:
              - `unified` — edinaja stavka
              - `manual` — ruchnaja stavka
    """

    id: int
    nm_settings: List["AuctionAdvertNMsSettings"]
    settings: "AuctionAdvertSettings"
    status: GetAuctionAdvertsAdvertsItemStatus
    timestamps: "Timestamps"
    bid_type: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        nm_settings = []
        for nm_settings_item_data in self.nm_settings:
            nm_settings_item = nm_settings_item_data.to_dict()
            nm_settings.append(nm_settings_item)

        settings = self.settings.to_dict()

        status = self.status.value

        timestamps = self.timestamps.to_dict()

        bid_type = self.bid_type

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "nm_settings": nm_settings,
                "settings": settings,
                "status": status,
                "timestamps": timestamps,
                "bid_type": bid_type,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.auction_advert_n_ms_settings import AuctionAdvertNMsSettings
        from ..models.auction_advert_settings import AuctionAdvertSettings
        from ..models.timestamps import Timestamps

        d = src_dict.copy()
        id = d.pop("id")

        nm_settings = []
        _nm_settings = d.pop("nm_settings")
        for nm_settings_item_data in _nm_settings:
            nm_settings_item = AuctionAdvertNMsSettings.from_dict(nm_settings_item_data)

            nm_settings.append(nm_settings_item)

        settings = AuctionAdvertSettings.from_dict(d.pop("settings"))

        status = GetAuctionAdvertsAdvertsItemStatus(d.pop("status"))

        timestamps = Timestamps.from_dict(d.pop("timestamps"))

        bid_type = d.pop("bid_type")

        get_auction_adverts_adverts_item = cls(
            id=id,
            nm_settings=nm_settings,
            settings=settings,
            status=status,
            timestamps=timestamps,
            bid_type=bid_type,
        )

        get_auction_adverts_adverts_item.additional_properties = d
        return get_auction_adverts_adverts_item

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
