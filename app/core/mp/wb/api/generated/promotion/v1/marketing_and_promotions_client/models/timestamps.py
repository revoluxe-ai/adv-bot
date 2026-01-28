from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="Timestamps")


@_attrs_define
class Timestamps:
    """Timestamps

    Attributes:
        created (datetime.datetime): Campaign create time
        updated (datetime.datetime): Campaign last update time
        started (datetime.datetime): Campaign launch time
        deleted (datetime.datetime): Campaign delete date. If the campaign has not been deleted, the time is indicated
            in the future
    """

    created: datetime.datetime
    updated: datetime.datetime
    started: datetime.datetime
    deleted: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        created = self.created.isoformat()

        updated = self.updated.isoformat()

        started = self.started.isoformat()

        deleted = self.deleted.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "created": created,
            "updated": updated,
            "started": started,
            "deleted": deleted,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        created = isoparse(d.pop("created"))

        updated = isoparse(d.pop("updated"))

        started = isoparse(d.pop("started"))

        deleted = isoparse(d.pop("deleted"))

        timestamps = cls(
            created=created,
            updated=updated,
            started=started,
            deleted=deleted,
        )

        timestamps.additional_properties = d
        return timestamps

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
