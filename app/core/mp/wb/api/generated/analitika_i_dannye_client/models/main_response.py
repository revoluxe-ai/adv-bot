from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.common_info import CommonInfo
    from ..models.position_info import PositionInfo
    from ..models.table_group_item import TableGroupItem
    from ..models.visibility_info import VisibilityInfo


T = TypeVar("T", bound="MainResponse")


@_attrs_define
class MainResponse:
    """
    Attributes:
        common_info (CommonInfo): Obschaja informatsija
        position_info (PositionInfo): Informatsija o pozitsii tovara
        visibility_info (VisibilityInfo): Vidimost' kartochek i perehody v kartochki. Po dnjam, nedeljam, mesjatsam
        groups (Union[Unset, List['TableGroupItem']]): Spisok elementov tablitsy
    """

    common_info: "CommonInfo"
    position_info: "PositionInfo"
    visibility_info: "VisibilityInfo"
    groups: Union[Unset, List["TableGroupItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        common_info = self.common_info.to_dict()

        position_info = self.position_info.to_dict()

        visibility_info = self.visibility_info.to_dict()

        groups: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.groups, Unset):
            groups = []
            for groups_item_data in self.groups:
                groups_item = groups_item_data.to_dict()
                groups.append(groups_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "commonInfo": common_info,
                "positionInfo": position_info,
                "visibilityInfo": visibility_info,
            }
        )
        if groups is not UNSET:
            field_dict["groups"] = groups

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.common_info import CommonInfo
        from ..models.position_info import PositionInfo
        from ..models.table_group_item import TableGroupItem
        from ..models.visibility_info import VisibilityInfo

        d = src_dict.copy()
        common_info = CommonInfo.from_dict(d.pop("commonInfo"))

        position_info = PositionInfo.from_dict(d.pop("positionInfo"))

        visibility_info = VisibilityInfo.from_dict(d.pop("visibilityInfo"))

        groups = []
        _groups = d.pop("groups", UNSET)
        for groups_item_data in _groups or []:
            groups_item = TableGroupItem.from_dict(groups_item_data)

            groups.append(groups_item)

        main_response = cls(
            common_info=common_info,
            position_info=position_info,
            visibility_info=visibility_info,
            groups=groups,
        )

        main_response.additional_properties = d
        return main_response

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
