from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.v0_advert_multi_bid_item import V0AdvertMultiBidItem


T = TypeVar("T", bound="V0AdvertMultibid")


@_attrs_define
class V0AdvertMultibid:
    """
    Attributes:
        advert_id (int): ID kampanii Example: 6348555.
        nm_bids (list['V0AdvertMultiBidItem']): Artikuly WB i stavki dlja nih
    """

    advert_id: int
    nm_bids: list["V0AdvertMultiBidItem"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        nm_bids = []
        for nm_bids_item_data in self.nm_bids:
            nm_bids_item = nm_bids_item_data.to_dict()
            nm_bids.append(nm_bids_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nm_bids": nm_bids,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.v0_advert_multi_bid_item import V0AdvertMultiBidItem

        d = dict(src_dict)
        advert_id = d.pop("advert_id")

        nm_bids = []
        _nm_bids = d.pop("nm_bids")
        for nm_bids_item_data in _nm_bids:
            nm_bids_item = V0AdvertMultiBidItem.from_dict(nm_bids_item_data)

            nm_bids.append(nm_bids_item)

        v0_advert_multibid = cls(
            advert_id=advert_id,
            nm_bids=nm_bids,
        )

        v0_advert_multibid.additional_properties = d
        return v0_advert_multibid

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
