from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.advert_bids_kopecks import AdvertBidsKopecks
    from ..models.advert_subject import AdvertSubject


T = TypeVar("T", bound="AdvertNMsSettings")


@_attrs_define
class AdvertNMsSettings:
    """
    Attributes:
        bids_kopecks (AdvertBidsKopecks): Stavki, kopejki
        subject (AdvertSubject): Predmet
        nm_id (int): Artikul WB
    """

    bids_kopecks: AdvertBidsKopecks
    subject: AdvertSubject
    nm_id: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bids_kopecks = self.bids_kopecks.to_dict()

        subject = self.subject.to_dict()

        nm_id = self.nm_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bids_kopecks": bids_kopecks,
                "subject": subject,
                "nm_id": nm_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any] | None) -> T:
        from ..models.advert_bids_kopecks import AdvertBidsKopecks
        from ..models.advert_subject import AdvertSubject

        d = dict(src_dict or {})
        bids_raw = d.pop("bids_kopecks", None)
        bids_kopecks = AdvertBidsKopecks.from_dict(
            bids_raw if bids_raw is not None else {"search": 0, "recommendations": 0}
        )

        subject_raw = d.pop("subject", None)
        subject = AdvertSubject.from_dict(
            subject_raw if subject_raw is not None else {"id": 0, "name": ""}
        )

        nm_id = d.pop("nm_id", None)
        if nm_id is None:
            nm_id = 0

        advert_n_ms_settings = cls(
            bids_kopecks=bids_kopecks,
            subject=subject,
            nm_id=nm_id,
        )

        advert_n_ms_settings.additional_properties = d
        return advert_n_ms_settings

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
