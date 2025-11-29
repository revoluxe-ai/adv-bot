from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.request_with_interval_interval import RequestWithIntervalInterval


T = TypeVar("T", bound="RequestWithInterval")


@_attrs_define
class RequestWithInterval:
    """
    Attributes:
        id (int): Campaign ID
        interval (RequestWithIntervalInterval): The time period for which information needs to be provided
    """

    id: int
    interval: RequestWithIntervalInterval
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.request_with_interval_interval import RequestWithIntervalInterval

        id = self.id

        interval = self.interval.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "interval": interval,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.request_with_interval_interval import RequestWithIntervalInterval

        d = dict(src_dict)
        id = d.pop("id")

        interval = RequestWithIntervalInterval.from_dict(d.pop("interval"))

        request_with_interval = cls(
            id=id,
            interval=interval,
        )

        request_with_interval.additional_properties = d
        return request_with_interval

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
