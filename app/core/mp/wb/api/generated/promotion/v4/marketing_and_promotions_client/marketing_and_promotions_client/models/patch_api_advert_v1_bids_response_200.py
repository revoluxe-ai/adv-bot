from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.patch_api_advert_v1_bids_response_200_bids_item import (
        PatchApiAdvertV1BidsResponse200BidsItem,
    )


T = TypeVar("T", bound="PatchApiAdvertV1BidsResponse200")


@_attrs_define
class PatchApiAdvertV1BidsResponse200:
    """
    Attributes:
        bids (List['PatchApiAdvertV1BidsResponse200BidsItem']): The result of processing the request
    """

    bids: List["PatchApiAdvertV1BidsResponse200BidsItem"]
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
        from ..models.patch_api_advert_v1_bids_response_200_bids_item import (
            PatchApiAdvertV1BidsResponse200BidsItem,
        )

        d = src_dict.copy()
        bids = []
        _bids = d.pop("bids")
        for bids_item_data in _bids:
            bids_item = PatchApiAdvertV1BidsResponse200BidsItem.from_dict(
                bids_item_data
            )

            bids.append(bids_item)

        patch_api_advert_v1_bids_response_200 = cls(
            bids=bids,
        )

        patch_api_advert_v1_bids_response_200.additional_properties = d
        return patch_api_advert_v1_bids_response_200

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
