from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_auction_adverts_adverts_item_status import (
    GetAuctionAdvertsAdvertsItemStatus,
)
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.auction_advert_n_ms_settings import AuctionAdvertNMsSettings
    from ..models.auction_advert_settings import AuctionAdvertSettings
    from ..models.timestamps import Timestamps


T = TypeVar("T", bound="GetAuctionAdvertsAdvertsItem")


@_attrs_define
class GetAuctionAdvertsAdvertsItem:
    """
    Attributes:
        id (int): Campaign ID
        nm_settings (list[AuctionAdvertNMsSettings]): Product settings
        settings (AuctionAdvertSettings): Campaign settings
        status (GetAuctionAdvertsAdvertsItemStatus): Campaign status:
            - `-1` — deleted, the deletion process will be completed within 10 minutes
            - `4` — ready to be launched
            - `7` — completed
            - `8` — declined
            - `9` — active
            - `11` — campaign is paused
        timestamps (Timestamps): Timestamps
        bid_type (str): Bid type:
              - `unified` — standard bid
              - `manual` — custom bid
    """

    id: int
    nm_settings: list[AuctionAdvertNMsSettings]
    settings: AuctionAdvertSettings
    status: GetAuctionAdvertsAdvertsItemStatus
    timestamps: Timestamps
    bid_type: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.auction_advert_n_ms_settings import AuctionAdvertNMsSettings
        from ..models.auction_advert_settings import AuctionAdvertSettings
        from ..models.timestamps import Timestamps

        id = self.id

        nm_settings = []
        for nm_settings_item_data in self.nm_settings:
            nm_settings_item = nm_settings_item_data.to_dict()
            nm_settings.append(nm_settings_item)

        settings = self.settings.to_dict()

        status = self.status.value

        timestamps = self.timestamps.to_dict()

        bid_type = self.bid_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "nm_settings": nm_settings,
            "settings": settings,
            "status": status,
            "timestamps": timestamps,
            "bid_type": bid_type,
        })

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
