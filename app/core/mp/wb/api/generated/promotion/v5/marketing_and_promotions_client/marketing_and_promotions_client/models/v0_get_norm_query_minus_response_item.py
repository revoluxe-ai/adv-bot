from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="V0GetNormQueryMinusResponseItem")


@_attrs_define
class V0GetNormQueryMinusResponseItem:
    """
    Attributes:
        advert_id (Union[Unset, int]): Campaign ID
        nm_id (Union[Unset, int]): WB article
        norm_queries (Union[Unset, List[str]]): List of minus-phrases
    """

    advert_id: Union[Unset, int] = UNSET
    nm_id: Union[Unset, int] = UNSET
    norm_queries: Union[Unset, List[str]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        norm_queries: Union[Unset, List[str]] = UNSET
        if not isinstance(self.norm_queries, Unset):
            norm_queries = self.norm_queries

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if advert_id is not UNSET:
            field_dict["advert_id"] = advert_id
        if nm_id is not UNSET:
            field_dict["nm_id"] = nm_id
        if norm_queries is not UNSET:
            field_dict["norm_queries"] = norm_queries

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        advert_id = d.pop("advert_id", UNSET)

        nm_id = d.pop("nm_id", UNSET)

        norm_queries = cast(List[str], d.pop("norm_queries", UNSET))

        v0_get_norm_query_minus_response_item = cls(
            advert_id=advert_id,
            nm_id=nm_id,
            norm_queries=norm_queries,
        )

        v0_get_norm_query_minus_response_item.additional_properties = d
        return v0_get_norm_query_minus_response_item

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
