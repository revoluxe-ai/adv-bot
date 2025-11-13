from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="V0SetNormQueryBidsRequestItem")


@_attrs_define
class V0SetNormQueryBidsRequestItem:
    """
    Attributes:
        advert_id (int): ID kampanii
        nm_id (int): Artikul WB
        norm_query (str): Poiskovyj klaster
        bid (int): Stavka za tysjachu pokazov, ₽
    """

    advert_id: int
    nm_id: int
    norm_query: str
    bid: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        norm_query = self.norm_query

        bid = self.bid

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nm_id": nm_id,
                "norm_query": norm_query,
                "bid": bid,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        advert_id = d.pop("advert_id")

        nm_id = d.pop("nm_id")

        norm_query = d.pop("norm_query")

        bid = d.pop("bid")

        v0_set_norm_query_bids_request_item = cls(
            advert_id=advert_id,
            nm_id=nm_id,
            norm_query=norm_query,
            bid=bid,
        )

        v0_set_norm_query_bids_request_item.additional_properties = d
        return v0_set_norm_query_bids_request_item

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
