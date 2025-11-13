from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.auction_advert_bids import AuctionAdvertBids
    from ..models.auction_advert_subject import AuctionAdvertSubject


T = TypeVar("T", bound="AuctionAdvertNMsSettings")


@_attrs_define
class AuctionAdvertNMsSettings:
    """
    Attributes:
        bids (AuctionAdvertBids): Stavki
        subject (AuctionAdvertSubject): Predmet
        nm_id (int): Artikul WB
    """

    bids: "AuctionAdvertBids"
    subject: "AuctionAdvertSubject"
    nm_id: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        bids = self.bids.to_dict()

        subject = self.subject.to_dict()

        nm_id = self.nm_id

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bids": bids,
                "subject": subject,
                "nm_id": nm_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.auction_advert_bids import AuctionAdvertBids
        from ..models.auction_advert_subject import AuctionAdvertSubject

        d = src_dict.copy()
        bids = AuctionAdvertBids.from_dict(d.pop("bids"))

        subject = AuctionAdvertSubject.from_dict(d.pop("subject"))

        nm_id = d.pop("nm_id")

        auction_advert_n_ms_settings = cls(
            bids=bids,
            subject=subject,
            nm_id=nm_id,
        )

        auction_advert_n_ms_settings.additional_properties = d
        return auction_advert_n_ms_settings

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
