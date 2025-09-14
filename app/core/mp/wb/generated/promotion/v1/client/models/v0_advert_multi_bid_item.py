from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="V0AdvertMultiBidItem")


@_attrs_define
class V0AdvertMultiBidItem:
    """
    Attributes:
        nm (int): Artikul WB Example: 3462354.
        bid (int): Stavka. Minimal'no dopustimye stavki vy mozhete poluchit' v otvete metoda [poluchenija minimal'nyh
            stavok dlja kartochek tovarov](./promotion#tag/Sozdanie-kampanij/paths/~1adv~1v0~1bids~1min/post) Example: 500.
    """

    nm: int
    bid: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm = self.nm

        bid = self.bid

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nm": nm,
                "bid": bid,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm = d.pop("nm")

        bid = d.pop("bid")

        v0_advert_multi_bid_item = cls(
            nm=nm,
            bid=bid,
        )

        v0_advert_multi_bid_item.additional_properties = d
        return v0_advert_multi_bid_item

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
