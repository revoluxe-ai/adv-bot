from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetApiV2HistoryTasksResponse429")


@_attrs_define
class GetApiV2HistoryTasksResponse429:
    """
    Attributes:
        title (str | Unset): Zagolovok oshibki
        detail (str | Unset): Detali oshibki
        code (str | Unset): Vnutrennij kod oshibki
        request_id (str | Unset): Unikal'nyj ID zaprosa
        origin (str | Unset): ID vnutrennego servisa WB
        status (float | Unset): HTTP status-kod
        status_text (str | Unset): Rasshifrovka HTTP status-koda
        timestamp (datetime.datetime | Unset): Data i vremja zaprosa
    """

    title: str | Unset = UNSET
    detail: str | Unset = UNSET
    code: str | Unset = UNSET
    request_id: str | Unset = UNSET
    origin: str | Unset = UNSET
    status: float | Unset = UNSET
    status_text: str | Unset = UNSET
    timestamp: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        detail = self.detail

        code = self.code

        request_id = self.request_id

        origin = self.origin

        status = self.status

        status_text = self.status_text

        timestamp: str | Unset = UNSET
        if not isinstance(self.timestamp, Unset):
            timestamp = self.timestamp.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if title is not UNSET:
            field_dict["title"] = title
        if detail is not UNSET:
            field_dict["detail"] = detail
        if code is not UNSET:
            field_dict["code"] = code
        if request_id is not UNSET:
            field_dict["requestId"] = request_id
        if origin is not UNSET:
            field_dict["origin"] = origin
        if status is not UNSET:
            field_dict["status"] = status
        if status_text is not UNSET:
            field_dict["statusText"] = status_text
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title", UNSET)

        detail = d.pop("detail", UNSET)

        code = d.pop("code", UNSET)

        request_id = d.pop("requestId", UNSET)

        origin = d.pop("origin", UNSET)

        status = d.pop("status", UNSET)

        status_text = d.pop("statusText", UNSET)

        _timestamp = d.pop("timestamp", UNSET)
        timestamp: datetime.datetime | Unset
        if isinstance(_timestamp, Unset):
            timestamp = UNSET
        else:
            timestamp = isoparse(_timestamp)

        get_api_v2_history_tasks_response_429 = cls(
            title=title,
            detail=detail,
            code=code,
            request_id=request_id,
            origin=origin,
            status=status,
            status_text=status_text,
            timestamp=timestamp,
        )

        get_api_v2_history_tasks_response_429.additional_properties = d
        return get_api_v2_history_tasks_response_429

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
