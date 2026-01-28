from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="Timestamps")


@_attrs_define
class Timestamps:
    """Vremennye otmetki

    Attributes:
        created (datetime.datetime): Vremja sozdanija kampanii
        updated (datetime.datetime): Vremja poslednego izmenenija kampanii
        started (datetime.datetime | None): Vremja poslednego zapuska kampanii
        deleted (datetime.datetime): Vremja udalenija kampanii. Esli kampanija ne udalena, vremja ukazyvaetsja v
            buduschem
    """

    created: datetime.datetime
    updated: datetime.datetime
    started: datetime.datetime | None
    deleted: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        created = self.created.isoformat()

        updated = self.updated.isoformat()

        started: None | str
        if isinstance(self.started, datetime.datetime):
            started = self.started.isoformat()
        else:
            started = self.started

        deleted = self.deleted.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "created": created,
                "updated": updated,
                "started": started,
                "deleted": deleted,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        created = isoparse(d.pop("created"))

        updated = isoparse(d.pop("updated"))

        def _parse_started(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                started_type_0 = isoparse(data)

                return started_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        started = _parse_started(d.pop("started"))

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
