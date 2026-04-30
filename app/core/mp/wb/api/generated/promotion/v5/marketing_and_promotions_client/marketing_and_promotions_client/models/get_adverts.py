from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.get_adverts_adverts_item import GetAdvertsAdvertsItem


T = TypeVar("T", bound="GetAdverts")


@_attrs_define
class GetAdverts:
    """
    Attributes:
        adverts (List['GetAdvertsAdvertsItem']): Campaigns
    """

    adverts: List["GetAdvertsAdvertsItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        adverts = []
        for adverts_item_data in self.adverts:
            adverts_item = adverts_item_data.to_dict()
            adverts.append(adverts_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "adverts": adverts,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_adverts_adverts_item import GetAdvertsAdvertsItem

        d = src_dict.copy()
        adverts = []
        _adverts = d.pop("adverts")
        for adverts_item_data in _adverts:
            adverts_item = GetAdvertsAdvertsItem.from_dict(adverts_item_data)

            adverts.append(adverts_item)

        get_adverts = cls(
            adverts=adverts,
        )

        get_adverts.additional_properties = d
        return get_adverts

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
