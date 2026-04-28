from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.v0_get_norm_query_list_response_item import (
        V0GetNormQueryListResponseItem,
    )


T = TypeVar("T", bound="V0GetNormQueryListResponse")


@_attrs_define
class V0GetNormQueryListResponse:
    """
    Attributes:
        items (Union[List['V0GetNormQueryListResponseItem'], None]):
    """

    items: Union[List["V0GetNormQueryListResponseItem"], None]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        items: Union[List[Dict[str, Any]], None]
        if isinstance(self.items, list):
            items = []
            for items_type_0_item_data in self.items:
                items_type_0_item = items_type_0_item_data.to_dict()
                items.append(items_type_0_item)

        else:
            items = self.items

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "items": items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_get_norm_query_list_response_item import (
            V0GetNormQueryListResponseItem,
        )

        d = src_dict.copy()

        def _parse_items(
            data: object,
        ) -> Union[List["V0GetNormQueryListResponseItem"], None]:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                items_type_0 = []
                _items_type_0 = data
                for items_type_0_item_data in _items_type_0:
                    items_type_0_item = V0GetNormQueryListResponseItem.from_dict(
                        items_type_0_item_data
                    )

                    items_type_0.append(items_type_0_item)

                return items_type_0
            except:  # noqa: E722
                pass
            return cast(Union[List["V0GetNormQueryListResponseItem"], None], data)

        items = _parse_items(d.pop("items"))

        v0_get_norm_query_list_response = cls(
            items=items,
        )

        v0_get_norm_query_list_response.additional_properties = d
        return v0_get_norm_query_list_response

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
