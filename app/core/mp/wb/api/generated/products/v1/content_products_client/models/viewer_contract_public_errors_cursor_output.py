from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="ViewerContractPublicErrorsCursorOutput")


@_attrs_define
class ViewerContractPublicErrorsCursorOutput:
    """Paginator

    Attributes:
        next_ (bool): Est' li esche chernoviki:
              - `false` — net
              - `true` — da
        updated_at (datetime.datetime): Data i vremja formirovanija poslednego paketa v otvete
        batch_uuid (str): ID poslednego paketa v otvete
    """

    next_: bool
    updated_at: datetime.datetime
    batch_uuid: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        next_ = self.next_

        updated_at = self.updated_at.isoformat()

        batch_uuid = self.batch_uuid

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "next": next_,
                "updatedAt": updated_at,
                "batchUUID": batch_uuid,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        next_ = d.pop("next")

        updated_at = isoparse(d.pop("updatedAt"))

        batch_uuid = d.pop("batchUUID")

        viewer_contract_public_errors_cursor_output = cls(
            next_=next_,
            updated_at=updated_at,
            batch_uuid=batch_uuid,
        )

        viewer_contract_public_errors_cursor_output.additional_properties = d
        return viewer_contract_public_errors_cursor_output

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
