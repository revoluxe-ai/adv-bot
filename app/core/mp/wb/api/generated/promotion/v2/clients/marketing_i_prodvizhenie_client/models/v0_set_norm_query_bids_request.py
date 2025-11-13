from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.v0_set_norm_query_bids_request_item import V0SetNormQueryBidsRequestItem


T = TypeVar("T", bound="V0SetNormQueryBidsRequest")


@_attrs_define
class V0SetNormQueryBidsRequest:
    """
    Attributes:
        bids (List['V0SetNormQueryBidsRequestItem']):
    """

    bids: List["V0SetNormQueryBidsRequestItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        bids = []
        for bids_item_data in self.bids:
            bids_item = bids_item_data.to_dict()
            bids.append(bids_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bids": bids,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_set_norm_query_bids_request_item import V0SetNormQueryBidsRequestItem

        d = src_dict.copy()
        bids = []
        _bids = d.pop("bids")
        for bids_item_data in _bids:
            bids_item = V0SetNormQueryBidsRequestItem.from_dict(bids_item_data)

            bids.append(bids_item)

        v0_set_norm_query_bids_request = cls(
            bids=bids,
        )

        v0_set_norm_query_bids_request.additional_properties = d
        return v0_set_norm_query_bids_request

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
