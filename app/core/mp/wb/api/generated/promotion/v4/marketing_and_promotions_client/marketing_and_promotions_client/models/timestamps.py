import datetime
from typing import (
    Any,
    Dict,
    List,
    Type,
    TypeVar,
    Union,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="Timestamps")


@_attrs_define
class Timestamps:
    """Timestamps

    Attributes:
        created (datetime.datetime): Campaign create time
        updated (datetime.datetime): Campaign last update time
        started (Union[None, datetime.datetime]): Campaign launch time
        deleted (datetime.datetime): Campaign delete date. If the campaign has not been deleted, the time will be
            indicated in the future
    """

    created: datetime.datetime
    updated: datetime.datetime
    started: Union[None, datetime.datetime]
    deleted: datetime.datetime
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        created = self.created.isoformat()

        updated = self.updated.isoformat()

        started: Union[None, str]
        if isinstance(self.started, datetime.datetime):
            started = self.started.isoformat()
        else:
            started = self.started

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

        def _parse_started(data: object) -> Union[None, datetime.datetime]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                started_type_0 = isoparse(data)

                return started_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, datetime.datetime], data)

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
