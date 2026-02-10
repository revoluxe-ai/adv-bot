from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="SwaggerPublicErrorsCursorInput")


@_attrs_define
class SwaggerPublicErrorsCursorInput:
    """Paginator

    Attributes:
        limit (float | Unset): Kolichestvo paketov v otvete Default: 100.0.
        updated_at (datetime.datetime | Unset): Data i vremja formirovanija poslednego paketa v otvete na predyduschij
            zapros
        batch_uuid (str | Unset): ID poslednego paketa v otvete na predyduschij zapros
    """

    limit: float | Unset = 100.0
    updated_at: datetime.datetime | Unset = UNSET
    batch_uuid: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        limit = self.limit

        updated_at: str | Unset = UNSET
        if not isinstance(self.updated_at, Unset):
            updated_at = self.updated_at.isoformat()

        batch_uuid = self.batch_uuid

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if limit is not UNSET:
            field_dict["limit"] = limit
        if updated_at is not UNSET:
            field_dict["updatedAt"] = updated_at
        if batch_uuid is not UNSET:
            field_dict["batchUUID"] = batch_uuid

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        limit = d.pop("limit", UNSET)

        _updated_at = d.pop("updatedAt", UNSET)
        updated_at: datetime.datetime | Unset
        if isinstance(_updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = isoparse(_updated_at)

        batch_uuid = d.pop("batchUUID", UNSET)

        swagger_public_errors_cursor_input = cls(
            limit=limit,
            updated_at=updated_at,
            batch_uuid=batch_uuid,
        )

        swagger_public_errors_cursor_input.additional_properties = d
        return swagger_public_errors_cursor_input

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
