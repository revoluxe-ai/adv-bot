from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_auction_adverts import GetAuctionAdverts


T = TypeVar("T", bound="GetAdvV0AuctionAdvertsResponse200")


@_attrs_define
class GetAdvV0AuctionAdvertsResponse200:
    """
    Attributes:
        adverts (Union[Unset, list['GetAuctionAdverts']]): Kampanii
    """

    adverts: Union[Unset, list["GetAuctionAdverts"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        adverts: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.adverts, Unset):
            adverts = []
            for adverts_item_data in self.adverts:
                adverts_item = adverts_item_data.to_dict()
                adverts.append(adverts_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if adverts is not UNSET:
            field_dict["adverts"] = adverts

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_auction_adverts import GetAuctionAdverts

        d = dict(src_dict)
        adverts = []
        _adverts = d.pop("adverts", UNSET)
        for adverts_item_data in _adverts or []:
            adverts_item = GetAuctionAdverts.from_dict(adverts_item_data)

            adverts.append(adverts_item)

        get_adv_v0_auction_adverts_response_200 = cls(
            adverts=adverts,
        )

        get_adv_v0_auction_adverts_response_200.additional_properties = d
        return get_adv_v0_auction_adverts_response_200

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
