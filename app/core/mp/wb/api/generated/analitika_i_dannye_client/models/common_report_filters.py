from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.availability_filters_item import AvailabilityFiltersItem
from ..models.stock_type import StockType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.period_st import PeriodSt
    from ..models.table_order_by import TableOrderBy


T = TypeVar("T", bound="CommonReportFilters")


@_attrs_define
class CommonReportFilters:
    """Obschie fil'try po otchetu

    Attributes:
        current_period (PeriodSt): Period
        stock_type (StockType): Tip skladov hranenija tovarov:
              - `""` — vse
              - `wb` — Sklady WB
              - `mp` — Sklady Marketplejs (FBS)
             Example: mp.
        skip_deleted_nm (bool): Skryt' udalennye tovary Example: True.
        availability_filters (List[AvailabilityFiltersItem]): Dostupnost' tovara:
              - `deficient` — Defitsit
              - `actual` — Aktual'nyj
              - `balanced` — Balans
              - `nonActual` — Neaktual'nyj
              - `nonLiquid` — Nelikvid
              - `invalidData` — Ne rasschitano
             Example: ['deficient', 'balanced'].
        order_by (TableOrderBy): Vid sortirovki dannyh
        nm_i_ds (Union[Unset, List[int]]): Spisok artikulov WB dlja fil'tratsii Example: [111222333, 444555666].
        subject_i_ds (Union[Unset, List[int]]): Spisok ID predmetov dlja fil'tratsii Example: [123, 456].
        brand_names (Union[Unset, List[str]]): Spisok brendov dlja fil'tratsii Example: ['Erk', 'Dent'].
        tag_i_ds (Union[Unset, List[int]]): Spisok ID jarlykov dlja fil'tratsii Example: [3, 4, 5].
    """

    current_period: "PeriodSt"
    stock_type: StockType
    skip_deleted_nm: bool
    availability_filters: List[AvailabilityFiltersItem]
    order_by: "TableOrderBy"
    nm_i_ds: Union[Unset, List[int]] = UNSET
    subject_i_ds: Union[Unset, List[int]] = UNSET
    brand_names: Union[Unset, List[str]] = UNSET
    tag_i_ds: Union[Unset, List[int]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current_period = self.current_period.to_dict()

        stock_type = self.stock_type.value

        skip_deleted_nm = self.skip_deleted_nm

        availability_filters = []
        for componentsschemasavailability_filters_item_data in self.availability_filters:
            componentsschemasavailability_filters_item = componentsschemasavailability_filters_item_data.value
            availability_filters.append(componentsschemasavailability_filters_item)

        order_by = self.order_by.to_dict()

        nm_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nm_i_ds, Unset):
            nm_i_ds = self.nm_i_ds

        subject_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.subject_i_ds, Unset):
            subject_i_ds = self.subject_i_ds

        brand_names: Union[Unset, List[str]] = UNSET
        if not isinstance(self.brand_names, Unset):
            brand_names = self.brand_names

        tag_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.tag_i_ds, Unset):
            tag_i_ds = self.tag_i_ds

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "currentPeriod": current_period,
                "stockType": stock_type,
                "skipDeletedNm": skip_deleted_nm,
                "availabilityFilters": availability_filters,
                "orderBy": order_by,
            }
        )
        if nm_i_ds is not UNSET:
            field_dict["nmIDs"] = nm_i_ds
        if subject_i_ds is not UNSET:
            field_dict["subjectIDs"] = subject_i_ds
        if brand_names is not UNSET:
            field_dict["brandNames"] = brand_names
        if tag_i_ds is not UNSET:
            field_dict["tagIDs"] = tag_i_ds

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.period_st import PeriodSt
        from ..models.table_order_by import TableOrderBy

        d = src_dict.copy()
        current_period = PeriodSt.from_dict(d.pop("currentPeriod"))

        stock_type = StockType(d.pop("stockType"))

        skip_deleted_nm = d.pop("skipDeletedNm")

        availability_filters = []
        _availability_filters = d.pop("availabilityFilters")
        for componentsschemasavailability_filters_item_data in _availability_filters:
            componentsschemasavailability_filters_item = AvailabilityFiltersItem(
                componentsschemasavailability_filters_item_data
            )

            availability_filters.append(componentsschemasavailability_filters_item)

        order_by = TableOrderBy.from_dict(d.pop("orderBy"))

        nm_i_ds = cast(List[int], d.pop("nmIDs", UNSET))

        subject_i_ds = cast(List[int], d.pop("subjectIDs", UNSET))

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        tag_i_ds = cast(List[int], d.pop("tagIDs", UNSET))

        common_report_filters = cls(
            current_period=current_period,
            stock_type=stock_type,
            skip_deleted_nm=skip_deleted_nm,
            availability_filters=availability_filters,
            order_by=order_by,
            nm_i_ds=nm_i_ds,
            subject_i_ds=subject_i_ds,
            brand_names=brand_names,
            tag_i_ds=tag_i_ds,
        )

        common_report_filters.additional_properties = d
        return common_report_filters

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
