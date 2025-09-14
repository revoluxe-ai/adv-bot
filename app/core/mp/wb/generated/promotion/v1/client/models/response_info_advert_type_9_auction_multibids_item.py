from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponseInfoAdvertType9AuctionMultibidsItem")


@_attrs_define
class ResponseInfoAdvertType9AuctionMultibidsItem:
    """
    Attributes:
        nm (Union[Unset, int]): Artikul WB
        bid (Union[Unset, int]): Stavka
    """

    nm: Union[Unset, int] = UNSET
    bid: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm = self.nm

        bid = self.bid

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm is not UNSET:
            field_dict["nm"] = nm
        if bid is not UNSET:
            field_dict["bid"] = bid

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm = d.pop("nm", UNSET)

        bid = d.pop("bid", UNSET)

        response_info_advert_type_9_auction_multibids_item = cls(
            nm=nm,
            bid=bid,
        )

        response_info_advert_type_9_auction_multibids_item.additional_properties = d
        return response_info_advert_type_9_auction_multibids_item

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
