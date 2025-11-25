from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.table_office_item import TableOfficeItem
    from ..models.table_size_response_sizes_item import TableSizeResponseSizesItem


T = TypeVar("T", bound="TableSizeResponse")


@_attrs_define
class TableSizeResponse:
    """
    Attributes:
        offices (Union[Unset, List['TableOfficeItem']]): Mnozhestvo dannyh po skladam
        sizes (Union[Unset, List['TableSizeResponseSizesItem']]): Mnozhestvo dannyh po razmeram tovara
    """

    offices: Union[Unset, List["TableOfficeItem"]] = UNSET
    sizes: Union[Unset, List["TableSizeResponseSizesItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        offices: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.offices, Unset):
            offices = []
            for offices_item_data in self.offices:
                offices_item = offices_item_data.to_dict()
                offices.append(offices_item)

        sizes: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.sizes, Unset):
            sizes = []
            for sizes_item_data in self.sizes:
                sizes_item = sizes_item_data.to_dict()
                sizes.append(sizes_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if offices is not UNSET:
            field_dict["offices"] = offices
        if sizes is not UNSET:
            field_dict["sizes"] = sizes

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_office_item import TableOfficeItem
        from ..models.table_size_response_sizes_item import TableSizeResponseSizesItem

        d = src_dict.copy()
        offices = []
        _offices = d.pop("offices", UNSET)
        for offices_item_data in _offices or []:
            offices_item = TableOfficeItem.from_dict(offices_item_data)

            offices.append(offices_item)

        sizes = []
        _sizes = d.pop("sizes", UNSET)
        for sizes_item_data in _sizes or []:
            sizes_item = TableSizeResponseSizesItem.from_dict(sizes_item_data)

            sizes.append(sizes_item)

        table_size_response = cls(
            offices=offices,
            sizes=sizes,
        )

        table_size_response.additional_properties = d
        return table_size_response

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
