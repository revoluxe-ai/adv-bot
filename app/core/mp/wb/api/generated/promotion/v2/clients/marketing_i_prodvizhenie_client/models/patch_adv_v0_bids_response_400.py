from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.patch_adv_v0_bids_response_400_errors_item import PatchAdvV0BidsResponse400ErrorsItem


T = TypeVar("T", bound="PatchAdvV0BidsResponse400")


@_attrs_define
class PatchAdvV0BidsResponse400:
    """
    Attributes:
        detail (Union[Unset, str]): Detali oshibki
        origin (Union[Unset, str]): ID vnutrennego servisa WB
        request_id (Union[Unset, str]): Unikal'nyj ID zaprosa
        status (Union[Unset, int]): HTTP status-kod
        title (Union[Unset, str]): Zagolovok oshibki
        errors (Union[Unset, List['PatchAdvV0BidsResponse400ErrorsItem']]): Detalizatsija oshibki
        type (Union[Unset, str]): Tip oshibki
    """

    detail: Union[Unset, str] = UNSET
    origin: Union[Unset, str] = UNSET
    request_id: Union[Unset, str] = UNSET
    status: Union[Unset, int] = UNSET
    title: Union[Unset, str] = UNSET
    errors: Union[Unset, List["PatchAdvV0BidsResponse400ErrorsItem"]] = UNSET
    type: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        detail = self.detail

        origin = self.origin

        request_id = self.request_id

        status = self.status

        title = self.title

        errors: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.errors, Unset):
            errors = []
            for errors_item_data in self.errors:
                errors_item = errors_item_data.to_dict()
                errors.append(errors_item)

        type = self.type

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if detail is not UNSET:
            field_dict["detail"] = detail
        if origin is not UNSET:
            field_dict["origin"] = origin
        if request_id is not UNSET:
            field_dict["request_id"] = request_id
        if status is not UNSET:
            field_dict["status"] = status
        if title is not UNSET:
            field_dict["title"] = title
        if errors is not UNSET:
            field_dict["errors"] = errors
        if type is not UNSET:
            field_dict["type"] = type

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.patch_adv_v0_bids_response_400_errors_item import PatchAdvV0BidsResponse400ErrorsItem

        d = src_dict.copy()
        detail = d.pop("detail", UNSET)

        origin = d.pop("origin", UNSET)

        request_id = d.pop("request_id", UNSET)

        status = d.pop("status", UNSET)

        title = d.pop("title", UNSET)

        errors = []
        _errors = d.pop("errors", UNSET)
        for errors_item_data in _errors or []:
            errors_item = PatchAdvV0BidsResponse400ErrorsItem.from_dict(errors_item_data)

            errors.append(errors_item)

        type = d.pop("type", UNSET)

        patch_adv_v0_bids_response_400 = cls(
            detail=detail,
            origin=origin,
            request_id=request_id,
            status=status,
            title=title,
            errors=errors,
            type=type,
        )

        patch_adv_v0_bids_response_400.additional_properties = d
        return patch_adv_v0_bids_response_400

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
