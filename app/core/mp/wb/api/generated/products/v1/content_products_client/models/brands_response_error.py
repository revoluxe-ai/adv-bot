from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.brands_response_error_errors_item import BrandsResponseErrorErrorsItem


T = TypeVar("T", bound="BrandsResponseError")


@_attrs_define
class BrandsResponseError:
    """
    Attributes:
        title (str): Zagolovok oshibki
        detail (str): Detali oshibki
        origin (str): ID vnutrennego servisa WB
        request_id (str): Unikal'nyj ID zaprosa
        errors (list[BrandsResponseErrorErrorsItem] | Unset):
    """

    title: str
    detail: str
    origin: str
    request_id: str
    errors: list[BrandsResponseErrorErrorsItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        detail = self.detail

        origin = self.origin

        request_id = self.request_id

        errors: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.errors, Unset):
            errors = []
            for errors_item_data in self.errors:
                errors_item = errors_item_data.to_dict()
                errors.append(errors_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "detail": detail,
                "origin": origin,
                "requestId": request_id,
            }
        )
        if errors is not UNSET:
            field_dict["errors"] = errors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.brands_response_error_errors_item import (
            BrandsResponseErrorErrorsItem,
        )

        d = dict(src_dict)
        title = d.pop("title")

        detail = d.pop("detail")

        origin = d.pop("origin")

        request_id = d.pop("requestId")

        _errors = d.pop("errors", UNSET)
        errors: list[BrandsResponseErrorErrorsItem] | Unset = UNSET
        if _errors is not UNSET:
            errors = []
            for errors_item_data in _errors:
                errors_item = BrandsResponseErrorErrorsItem.from_dict(errors_item_data)

                errors.append(errors_item)

        brands_response_error = cls(
            title=title,
            detail=detail,
            origin=origin,
            request_id=request_id,
            errors=errors,
        )

        brands_response_error.additional_properties = d
        return brands_response_error

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
