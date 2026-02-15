from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="V0GetNormQueryListResponseItemNormQueries")


@_attrs_define
class V0GetNormQueryListResponseItemNormQueries:
    """Search clusters

    Attributes:
        active (Union[List[str], None, Unset]): Active search clusters
        excluded (Union[List[str], None, Unset]): Inactive search clusters
    """

    active: Union[List[str], None, Unset] = UNSET
    excluded: Union[List[str], None, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        active: Union[List[str], None, Unset]
        if isinstance(self.active, Unset):
            active = UNSET
        elif isinstance(self.active, list):
            active = self.active

        else:
            active = self.active

        excluded: Union[List[str], None, Unset]
        if isinstance(self.excluded, Unset):
            excluded = UNSET
        elif isinstance(self.excluded, list):
            excluded = self.excluded

        else:
            excluded = self.excluded

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if active is not UNSET:
            field_dict["active"] = active
        if excluded is not UNSET:
            field_dict["excluded"] = excluded

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        def _parse_active(data: object) -> Union[List[str], None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                active_type_0 = cast(List[str], data)

                return active_type_0
            except:  # noqa: E722
                pass
            return cast(Union[List[str], None, Unset], data)

        active = _parse_active(d.pop("active", UNSET))

        def _parse_excluded(data: object) -> Union[List[str], None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                excluded_type_0 = cast(List[str], data)

                return excluded_type_0
            except:  # noqa: E722
                pass
            return cast(Union[List[str], None, Unset], data)

        excluded = _parse_excluded(d.pop("excluded", UNSET))

        v0_get_norm_query_list_response_item_norm_queries = cls(
            active=active,
            excluded=excluded,
        )

        v0_get_norm_query_list_response_item_norm_queries.additional_properties = d
        return v0_get_norm_query_list_response_item_norm_queries

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
