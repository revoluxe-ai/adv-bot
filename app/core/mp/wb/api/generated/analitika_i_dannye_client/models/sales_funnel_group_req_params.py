import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="SalesFunnelGroupReqParams")


@_attrs_define
class SalesFunnelGroupReqParams:
    """Parametry otcheta

    Attributes:
        start_date (datetime.date): Nachalo perioda
        end_date (datetime.date): Konets perioda
        subject_ids (Union[Unset, List[int]]): Spisok ID predmetov dlja fil'tratsii Example: [64, 334].
        brand_names (Union[Unset, List[str]]): Spisok brendov dlja fil'tratsii Example: ['nike', 'adidas'].
        tag_ids (Union[Unset, List[int]]): Spisok ID jarlykov dlja fil'tratsii Example: [32, 53].
        timezone (Union[Unset, str]): Vremennaja zona, po umolchaniju Europe/Moscow
        aggregation_level (Union[Unset, str]): Kak sgruppirovat' dannye (po umolchaniju po dnjam):

              * `day` — po dnjam
              * `week` — po nedeljam
              * `month` — po mesjatsam
        skip_deleted_nm (Union[Unset, bool]): Skryt' udalennye `nmID`
    """

    start_date: datetime.date
    end_date: datetime.date
    subject_ids: Union[Unset, List[int]] = UNSET
    brand_names: Union[Unset, List[str]] = UNSET
    tag_ids: Union[Unset, List[int]] = UNSET
    timezone: Union[Unset, str] = UNSET
    aggregation_level: Union[Unset, str] = UNSET
    skip_deleted_nm: Union[Unset, bool] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        start_date = self.start_date.isoformat()

        end_date = self.end_date.isoformat()

        subject_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.subject_ids, Unset):
            subject_ids = self.subject_ids

        brand_names: Union[Unset, List[str]] = UNSET
        if not isinstance(self.brand_names, Unset):
            brand_names = self.brand_names

        tag_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.tag_ids, Unset):
            tag_ids = self.tag_ids

        timezone = self.timezone

        aggregation_level = self.aggregation_level

        skip_deleted_nm = self.skip_deleted_nm

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "startDate": start_date,
                "endDate": end_date,
            }
        )
        if subject_ids is not UNSET:
            field_dict["subjectIds"] = subject_ids
        if brand_names is not UNSET:
            field_dict["brandNames"] = brand_names
        if tag_ids is not UNSET:
            field_dict["tagIds"] = tag_ids
        if timezone is not UNSET:
            field_dict["timezone"] = timezone
        if aggregation_level is not UNSET:
            field_dict["aggregationLevel"] = aggregation_level
        if skip_deleted_nm is not UNSET:
            field_dict["skipDeletedNm"] = skip_deleted_nm

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        start_date = isoparse(d.pop("startDate")).date()

        end_date = isoparse(d.pop("endDate")).date()

        subject_ids = cast(List[int], d.pop("subjectIds", UNSET))

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        tag_ids = cast(List[int], d.pop("tagIds", UNSET))

        timezone = d.pop("timezone", UNSET)

        aggregation_level = d.pop("aggregationLevel", UNSET)

        skip_deleted_nm = d.pop("skipDeletedNm", UNSET)

        sales_funnel_group_req_params = cls(
            start_date=start_date,
            end_date=end_date,
            subject_ids=subject_ids,
            brand_names=brand_names,
            tag_ids=tag_ids,
            timezone=timezone,
            aggregation_level=aggregation_level,
            skip_deleted_nm=skip_deleted_nm,
        )

        sales_funnel_group_req_params.additional_properties = d
        return sales_funnel_group_req_params

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
