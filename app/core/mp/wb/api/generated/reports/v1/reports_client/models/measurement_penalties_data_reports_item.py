import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="MeasurementPenaltiesDataReportsItem")


@_attrs_define
class MeasurementPenaltiesDataReportsItem:
    """
    Attributes:
        nm_id (Union[Unset, int]): Wildberries article number Example: 123456789.
        subject_name (Union[Unset, str]): Subcategory Example: Костюмы спортивные.
        dim_id (Union[Unset, int]): Measurement ID Example: 123456789.
        prc_over (Union[Unset, float]): Difference in dimensions, % Example: 130.71.
        volume (Union[Unset, float]): Volume, l (as measured at warehouse) Example: 6.47.
        width (Union[Unset, int]): Width, cm (as measured at warehouse) Example: 7.
        length (Union[Unset, int]): Length, cm (as measured at warehouse) Example: 28.
        height (Union[Unset, int]): Height, cm (as measured at warehouse) Example: 33.
        volume_sup (Union[Unset, float]): Volume, L (as specified in listing) Example: 4.95.
        width_sup (Union[Unset, int]): Width, cm (as specified in listing) Example: 8.
        length_sup (Union[Unset, int]): Length, cm (as specified in listing) Example: 33.
        height_sup (Union[Unset, int]): Height, cm (as specified in listing) Example: 33.
        photo_urls (Union[Unset, List[str]]): Photos of the measurements Example: ['https://static-
            basket-09.wbbasket.ru/vol184/obmer-tovarov/measurement_on_table/wbs35154094220_em907759_n1_b2eaa5ed-
            bf21-4c58-b419-b5b5ec6f29ee.webp', 'https://static-basket-09.wbbasket.ru/vol184/obmer-
            tovarov/measurement_on_table/wbs35159094420_em907759_n2_040407b0-7752-4ae7-a4a4-7ec016e86511.webp',
            'https://static-basket-09.wbbasket.ru/vol184/obmer-
            tovarov/measurement_on_table/wbs35189094220_em904757_n3_9f502e24-3b3e-4efd-9hac-802813046ac3.webp'].
        dt_bonus (Union[Unset, datetime.datetime]): Fine date Example: 2025-06-02T00:00:00Z.
        is_valid (Union[Unset, bool]): Status of measurement
              - `false` — canceled
              - `true` — valid
             Example: True.
        is_valid_dt (Union[Unset, datetime.datetime]): Date and time of validation or cancellation of the measurement
            Example: 2025-05-29T13:35:57Z.
        reversal_amount (Union[Unset, float]): Reversal amount
        penalty_amount (Union[Unset, float]): Fine amount Example: 449.83.
    """

    nm_id: Union[Unset, int] = UNSET
    subject_name: Union[Unset, str] = UNSET
    dim_id: Union[Unset, int] = UNSET
    prc_over: Union[Unset, float] = UNSET
    volume: Union[Unset, float] = UNSET
    width: Union[Unset, int] = UNSET
    length: Union[Unset, int] = UNSET
    height: Union[Unset, int] = UNSET
    volume_sup: Union[Unset, float] = UNSET
    width_sup: Union[Unset, int] = UNSET
    length_sup: Union[Unset, int] = UNSET
    height_sup: Union[Unset, int] = UNSET
    photo_urls: Union[Unset, List[str]] = UNSET
    dt_bonus: Union[Unset, datetime.datetime] = UNSET
    is_valid: Union[Unset, bool] = UNSET
    is_valid_dt: Union[Unset, datetime.datetime] = UNSET
    reversal_amount: Union[Unset, float] = UNSET
    penalty_amount: Union[Unset, float] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        subject_name = self.subject_name

        dim_id = self.dim_id

        prc_over = self.prc_over

        volume = self.volume

        width = self.width

        length = self.length

        height = self.height

        volume_sup = self.volume_sup

        width_sup = self.width_sup

        length_sup = self.length_sup

        height_sup = self.height_sup

        photo_urls: Union[Unset, List[str]] = UNSET
        if not isinstance(self.photo_urls, Unset):
            photo_urls = self.photo_urls

        dt_bonus: Union[Unset, str] = UNSET
        if not isinstance(self.dt_bonus, Unset):
            dt_bonus = self.dt_bonus.isoformat()

        is_valid = self.is_valid

        is_valid_dt: Union[Unset, str] = UNSET
        if not isinstance(self.is_valid_dt, Unset):
            is_valid_dt = self.is_valid_dt.isoformat()

        reversal_amount = self.reversal_amount

        penalty_amount = self.penalty_amount

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if dim_id is not UNSET:
            field_dict["dimId"] = dim_id
        if prc_over is not UNSET:
            field_dict["prcOver"] = prc_over
        if volume is not UNSET:
            field_dict["volume"] = volume
        if width is not UNSET:
            field_dict["width"] = width
        if length is not UNSET:
            field_dict["length"] = length
        if height is not UNSET:
            field_dict["height"] = height
        if volume_sup is not UNSET:
            field_dict["volumeSup"] = volume_sup
        if width_sup is not UNSET:
            field_dict["widthSup"] = width_sup
        if length_sup is not UNSET:
            field_dict["lengthSup"] = length_sup
        if height_sup is not UNSET:
            field_dict["heightSup"] = height_sup
        if photo_urls is not UNSET:
            field_dict["photoUrls"] = photo_urls
        if dt_bonus is not UNSET:
            field_dict["dtBonus"] = dt_bonus
        if is_valid is not UNSET:
            field_dict["isValid"] = is_valid
        if is_valid_dt is not UNSET:
            field_dict["isValidDt"] = is_valid_dt
        if reversal_amount is not UNSET:
            field_dict["reversalAmount"] = reversal_amount
        if penalty_amount is not UNSET:
            field_dict["penaltyAmount"] = penalty_amount

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        nm_id = d.pop("nmId", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        dim_id = d.pop("dimId", UNSET)

        prc_over = d.pop("prcOver", UNSET)

        volume = d.pop("volume", UNSET)

        width = d.pop("width", UNSET)

        length = d.pop("length", UNSET)

        height = d.pop("height", UNSET)

        volume_sup = d.pop("volumeSup", UNSET)

        width_sup = d.pop("widthSup", UNSET)

        length_sup = d.pop("lengthSup", UNSET)

        height_sup = d.pop("heightSup", UNSET)

        photo_urls = cast(List[str], d.pop("photoUrls", UNSET))

        _dt_bonus = d.pop("dtBonus", UNSET)
        dt_bonus: Union[Unset, datetime.datetime]
        if isinstance(_dt_bonus, Unset):
            dt_bonus = UNSET
        else:
            dt_bonus = isoparse(_dt_bonus)

        is_valid = d.pop("isValid", UNSET)

        _is_valid_dt = d.pop("isValidDt", UNSET)
        is_valid_dt: Union[Unset, datetime.datetime]
        if isinstance(_is_valid_dt, Unset):
            is_valid_dt = UNSET
        else:
            is_valid_dt = isoparse(_is_valid_dt)

        reversal_amount = d.pop("reversalAmount", UNSET)

        penalty_amount = d.pop("penaltyAmount", UNSET)

        measurement_penalties_data_reports_item = cls(
            nm_id=nm_id,
            subject_name=subject_name,
            dim_id=dim_id,
            prc_over=prc_over,
            volume=volume,
            width=width,
            length=length,
            height=height,
            volume_sup=volume_sup,
            width_sup=width_sup,
            length_sup=length_sup,
            height_sup=height_sup,
            photo_urls=photo_urls,
            dt_bonus=dt_bonus,
            is_valid=is_valid,
            is_valid_dt=is_valid_dt,
            reversal_amount=reversal_amount,
            penalty_amount=penalty_amount,
        )

        measurement_penalties_data_reports_item.additional_properties = d
        return measurement_penalties_data_reports_item

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
