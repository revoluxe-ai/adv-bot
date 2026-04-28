from typing import Any, Dict, Type, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="RequestWithCampaignID")


@_attrs_define
class RequestWithCampaignID:
    """
    Attributes:
        id (int): Campaign ID
    """

    id: int

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "id": id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = d.pop("id")

        request_with_campaign_id = cls(
            id=id,
        )

        return request_with_campaign_id
