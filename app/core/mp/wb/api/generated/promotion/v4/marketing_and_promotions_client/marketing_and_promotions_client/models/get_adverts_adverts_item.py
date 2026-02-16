from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_adverts_adverts_item_status import GetAdvertsAdvertsItemStatus

if TYPE_CHECKING:
    from ..models.advert_n_ms_settings import AdvertNMsSettings
    from ..models.advert_settings import AdvertSettings
    from ..models.timestamps import Timestamps


T = TypeVar("T", bound="GetAdvertsAdvertsItem")


@_attrs_define
class GetAdvertsAdvertsItem:
    """
    Attributes:
        bid_type (str): Bid type:
              - `unified` — standard bid
              - `manual` — custom bid
        id (int): Campaign ID
        nm_settings (List['AdvertNMsSettings']): Product settings
        settings (AdvertSettings): Campaign settings
        status (GetAdvertsAdvertsItemStatus): Campaign status:
            - `-1` — deleted, the deletion process will be completed within 10 minutes
            - `4` — ready to be launched
            - `7` — completed
            - `8` — declined
            - `9` — active
            - `11` — campaign is paused
        timestamps (Timestamps): Timestamps
    """

    bid_type: str
    id: int
    nm_settings: List["AdvertNMsSettings"]
    settings: "AdvertSettings"
    status: GetAdvertsAdvertsItemStatus
    timestamps: "Timestamps"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        bid_type = self.bid_type

        id = self.id

        nm_settings = []
        for nm_settings_item_data in self.nm_settings:
            nm_settings_item = nm_settings_item_data.to_dict()
            nm_settings.append(nm_settings_item)

        settings = self.settings.to_dict()

        status = self.status.value

        timestamps = self.timestamps.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bid_type": bid_type,
                "id": id,
                "nm_settings": nm_settings,
                "settings": settings,
                "status": status,
                "timestamps": timestamps,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.advert_n_ms_settings import AdvertNMsSettings
        from ..models.advert_settings import AdvertSettings
        from ..models.timestamps import Timestamps

        d = src_dict.copy()
        bid_type = d.pop("bid_type")

        id = d.pop("id")

        nm_settings = []
        _nm_settings = d.pop("nm_settings")
        for nm_settings_item_data in _nm_settings:
            nm_settings_item = AdvertNMsSettings.from_dict(nm_settings_item_data)

            nm_settings.append(nm_settings_item)

        settings = AdvertSettings.from_dict(d.pop("settings"))

        status = GetAdvertsAdvertsItemStatus(d.pop("status"))

        timestamps = Timestamps.from_dict(d.pop("timestamps"))

        get_adverts_adverts_item = cls(
            bid_type=bid_type,
            id=id,
            nm_settings=nm_settings,
            settings=settings,
            status=status,
            timestamps=timestamps,
        )

        get_adverts_adverts_item.additional_properties = d
        return get_adverts_adverts_item

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
