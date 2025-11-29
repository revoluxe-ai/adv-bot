from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.patch_adv_v0_bids_response_400_errors_item import (
        PatchAdvV0BidsResponse400ErrorsItem,
    )


T = TypeVar("T", bound="PatchAdvV0BidsResponse400")


@_attrs_define
class PatchAdvV0BidsResponse400:
    """
    Attributes:
        detail (str | Unset): Error details
        origin (str | Unset): WB internal service ID
        request_id (str | Unset): Unique request ID
        status (int | Unset): HTTP status code
        title (str | Unset): Error title
        errors (list[PatchAdvV0BidsResponse400ErrorsItem] | Unset): Error details
        type_ (str | Unset): Error type
    """

    detail: str | Unset = UNSET
    origin: str | Unset = UNSET
    request_id: str | Unset = UNSET
    status: int | Unset = UNSET
    title: str | Unset = UNSET
    errors: list[PatchAdvV0BidsResponse400ErrorsItem] | Unset = UNSET
    type_: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.patch_adv_v0_bids_response_400_errors_item import (
            PatchAdvV0BidsResponse400ErrorsItem,
        )

        detail = self.detail

        origin = self.origin

        request_id = self.request_id

        status = self.status

        title = self.title

        errors: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.errors, Unset):
            errors = []
            for errors_item_data in self.errors:
                errors_item = errors_item_data.to_dict()
                errors.append(errors_item)

        type_ = self.type_

        field_dict: dict[str, Any] = {}
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
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.patch_adv_v0_bids_response_400_errors_item import (
            PatchAdvV0BidsResponse400ErrorsItem,
        )

        d = dict(src_dict)
        detail = d.pop("detail", UNSET)

        origin = d.pop("origin", UNSET)

        request_id = d.pop("request_id", UNSET)

        status = d.pop("status", UNSET)

        title = d.pop("title", UNSET)

        _errors = d.pop("errors", UNSET)
        errors: list[PatchAdvV0BidsResponse400ErrorsItem] | Unset = UNSET
        if _errors is not UNSET:
            errors = []
            for errors_item_data in _errors:
                errors_item = PatchAdvV0BidsResponse400ErrorsItem.from_dict(
                    errors_item_data
                )

                errors.append(errors_item)

        type_ = d.pop("type", UNSET)

        patch_adv_v0_bids_response_400 = cls(
            detail=detail,
            origin=origin,
            request_id=request_id,
            status=status,
            title=title,
            errors=errors,
            type_=type_,
        )

        patch_adv_v0_bids_response_400.additional_properties = d
        return patch_adv_v0_bids_response_400

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
