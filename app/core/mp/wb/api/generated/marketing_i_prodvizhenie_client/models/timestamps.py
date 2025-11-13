import datetime
from typing import Any, Dict, List, Type, TypeVar

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
        started (datetime.datetime): Vremja poslednego zapuska kampanii
        deleted (datetime.datetime): Vremja udalenija kampanii. Esli kampanija ne udalena, vremja ukazyvaetsja v
            buduschem
    """

    created: datetime.datetime
    updated: datetime.datetime
    started: datetime.datetime
    deleted: datetime.datetime
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        created = self.created.isoformat()

        updated = self.updated.isoformat()

        started = self.started.isoformat()

        deleted = self.deleted.isoformat()

        field_dict: Dict[str, Any] = {}
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
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
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
