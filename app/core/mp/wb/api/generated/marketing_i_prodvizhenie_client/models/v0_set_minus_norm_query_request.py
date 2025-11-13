from typing import Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="V0SetMinusNormQueryRequest")


@_attrs_define
class V0SetMinusNormQueryRequest:
    """
    Attributes:
        advert_id (int): ID kampanii
        nm_id (int): Artikul WB
        norm_queries (List[str]):
    """

    advert_id: int
    nm_id: int
    norm_queries: List[str]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        norm_queries = self.norm_queries

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nm_id": nm_id,
                "norm_queries": norm_queries,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        advert_id = d.pop("advert_id")

        nm_id = d.pop("nm_id")

        norm_queries = cast(List[str], d.pop("norm_queries"))

        v0_set_minus_norm_query_request = cls(
            advert_id=advert_id,
            nm_id=nm_id,
            norm_queries=norm_queries,
        )

        v0_set_minus_norm_query_request.additional_properties = d
        return v0_set_minus_norm_query_request

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
