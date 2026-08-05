from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_task_response_data import CreateTaskResponseData


T = TypeVar("T", bound="CreateTaskResponse")


@_attrs_define
class CreateTaskResponse:
    """
    Attributes:
        data (Union[Unset, CreateTaskResponseData]):
    """

    data: Union[Unset, "CreateTaskResponseData"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.create_task_response_data import CreateTaskResponseData

        d = src_dict.copy()
        _data = d.pop("data", UNSET)
        data: Union[Unset, CreateTaskResponseData]
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = CreateTaskResponseData.from_dict(_data)

        create_task_response = cls(
            data=data,
        )

        create_task_response.additional_properties = d
        return create_task_response

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
