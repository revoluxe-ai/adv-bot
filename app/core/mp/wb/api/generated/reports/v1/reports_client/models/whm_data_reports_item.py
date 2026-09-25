import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="WHMDataReportsItem")


@_attrs_define
class WHMDataReportsItem:
    """
    Attributes:
        nm_id (Union[Unset, int]): Wildberries article number Example: 123456789.
        subject_name (Union[Unset, str]): Subcategory
        dim_id (Union[Unset, int]): Measurement ID Example: 123456789.
        volume (Union[Unset, float]): Volume, l
        width (Union[Unset, int]): Width, cm Example: 66.
        length (Union[Unset, int]): Length, cm Example: 54.
        height (Union[Unset, int]): Height, cm Example: 11.
        photo_urls (Union[Unset, List[str]]): Photos of measurements Example: ['https://static-
            basket-03.wb.ru/vol54/handheld-goods-measurements-photo/8906416_a9f839da-c3b7-4ed6-737c-a9e731250fb0.jpg',
            'https://static-basket-03.wb.ru/vol54/handheld-goods-measurements-
            photo/8906416_2aac23b7-c8f9-42db-74e9-b4a9c916017c.jpg', 'https://static-basket-03.wb.ru/vol54/handheld-goods-
            measurements-photo/8906416_ff93b7c4-19d6-e0a2-4dba-7c2f09f06b3.jpg'].
        dt (Union[Unset, datetime.datetime]): Date and time Example: 2025-04-01T00:06:00Z.
    """

    nm_id: Union[Unset, int] = UNSET
    subject_name: Union[Unset, str] = UNSET
    dim_id: Union[Unset, int] = UNSET
    volume: Union[Unset, float] = UNSET
    width: Union[Unset, int] = UNSET
    length: Union[Unset, int] = UNSET
    height: Union[Unset, int] = UNSET
    photo_urls: Union[Unset, List[str]] = UNSET
    dt: Union[Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        subject_name = self.subject_name

        dim_id = self.dim_id

        volume = self.volume

        width = self.width

        length = self.length

        height = self.height

        photo_urls: Union[Unset, List[str]] = UNSET
        if not isinstance(self.photo_urls, Unset):
            photo_urls = self.photo_urls

        dt: Union[Unset, str] = UNSET
        if not isinstance(self.dt, Unset):
            dt = self.dt.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if dim_id is not UNSET:
            field_dict["dimId"] = dim_id
        if volume is not UNSET:
            field_dict["volume"] = volume
        if width is not UNSET:
            field_dict["width"] = width
        if length is not UNSET:
            field_dict["length"] = length
        if height is not UNSET:
            field_dict["height"] = height
        if photo_urls is not UNSET:
            field_dict["photoUrls"] = photo_urls
        if dt is not UNSET:
            field_dict["dt"] = dt

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        nm_id = d.pop("nmId", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        dim_id = d.pop("dimId", UNSET)

        volume = d.pop("volume", UNSET)

        width = d.pop("width", UNSET)

        length = d.pop("length", UNSET)

        height = d.pop("height", UNSET)

        photo_urls = cast(List[str], d.pop("photoUrls", UNSET))

        _dt = d.pop("dt", UNSET)
        dt: Union[Unset, datetime.datetime]
        if isinstance(_dt, Unset):
            dt = UNSET
        else:
            dt = isoparse(_dt)

        whm_data_reports_item = cls(
            nm_id=nm_id,
            subject_name=subject_name,
            dim_id=dim_id,
            volume=volume,
            width=width,
            length=length,
            height=height,
            photo_urls=photo_urls,
            dt=dt,
        )

        whm_data_reports_item.additional_properties = d
        return whm_data_reports_item

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
