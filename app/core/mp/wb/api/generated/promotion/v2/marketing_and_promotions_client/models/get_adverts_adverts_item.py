from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_adverts_adverts_item_status import GetAdvertsAdvertsItemStatus

if TYPE_CHECKING:
    from ..models.advert_n_ms_settings import AdvertNMsSettings
    from ..models.advert_settings import AdvertSettings
    from ..models.timestamps import Timestamps


T = TypeVar("T", bound="GetAdvertsAdvertsItem")

# WB may omit or null timestamps; Timestamps.from_dict requires ISO strings for non-optional fields.
_DEFAULT_TIMESTAMPS_DICT: dict[str, Any] = {
    "created": "1970-01-01T00:00:00+00:00",
    "updated": "1970-01-01T00:00:00+00:00",
    "started": None,
    "deleted": "1970-01-01T00:00:00+00:00",
}


@_attrs_define
class GetAdvertsAdvertsItem:
    """
    Attributes:
        bid_type (str): Tip stavki:
              - `unified` — edinaja stavka
              - `manual` — ruchnaja stavka
        id (int): ID kampanii
        nm_settings (list[AdvertNMsSettings]): Nastrojki tovarov
        settings (AdvertSettings): Nastrojki kampanii
        status (GetAdvertsAdvertsItemStatus): Status kampanii:
            - `-1` — udalena, protsess udalenija budet zavershen v techenie 10 minut
            - `4` — gotova k zapusku
            - `7` — zavershena
            - `8` — otmenena
            - `9` — aktivna
            - `11` — na pauze
        timestamps (Timestamps): Vremennye otmetki
    """

    bid_type: str
    id: int
    nm_settings: list[AdvertNMsSettings]
    settings: AdvertSettings
    status: GetAdvertsAdvertsItemStatus
    timestamps: Timestamps
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bid_type = self.bid_type

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
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.advert_n_ms_settings import AdvertNMsSettings
        from ..models.advert_settings import AdvertSettings
        from ..models.timestamps import Timestamps

        d = dict(src_dict)
        bid_type = d.pop("bid_type") or ""

        id = d.pop("id")

        nm_settings = []
        # WB may return null for nm_settings; OpenAPI client expected a list (TypeError otherwise).
        _nm_settings = d.pop("nm_settings", None) or []
        for nm_settings_item_data in _nm_settings:
            nm_settings_item = AdvertNMsSettings.from_dict(nm_settings_item_data)

            nm_settings.append(nm_settings_item)

        settings = AdvertSettings.from_dict(d.pop("settings", None))

        status = GetAdvertsAdvertsItemStatus(d.pop("status"))

        _ts = d.pop("timestamps", None)
        timestamps = Timestamps.from_dict(_ts if _ts is not None else _DEFAULT_TIMESTAMPS_DICT)

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
