from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_group_item_st import TableGroupItemSt


T = TypeVar("T", bound="TableGroupResponseSt")


@_attrs_define
class TableGroupResponseSt:
    """
    Attributes:
        groups (List['TableGroupItemSt']): Mnozhestvo dannyh po gruppam
    """

    groups: List["TableGroupItemSt"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        groups = []
        for componentsschemas_table_groups_item_data in self.groups:
            componentsschemas_table_groups_item = componentsschemas_table_groups_item_data.to_dict()
            groups.append(componentsschemas_table_groups_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "groups": groups,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_group_item_st import TableGroupItemSt

        d = src_dict.copy()
        groups = []
        _groups = d.pop("groups")
        for componentsschemas_table_groups_item_data in _groups:
            componentsschemas_table_groups_item = TableGroupItemSt.from_dict(componentsschemas_table_groups_item_data)

            groups.append(componentsschemas_table_groups_item)

        table_group_response_st = cls(
            groups=groups,
        )

        table_group_response_st.additional_properties = d
        return table_group_response_st

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
