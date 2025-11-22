from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.availability_filters_item import AvailabilityFiltersItem
from ..models.stock_type import StockType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.period_st import PeriodSt
    from ..models.table_order_by import TableOrderBy


T = TypeVar("T", bound="CommonProductFilters")


@_attrs_define
class CommonProductFilters:
    """Obschie fil'try po tovaru

    Attributes:
        current_period (PeriodSt): Period
        stock_type (StockType): Tip skladov hranenija tovarov:
              - `""` — vse
              - `wb` — Sklady WB
              - `mp` — Sklady Marketplejs (FBS)
             Example: mp.
        skip_deleted_nm (bool): Skryt' udalennye tovary Example: True.
        order_by (TableOrderBy): Vid sortirovki dannyh
        availability_filters (List[AvailabilityFiltersItem]): Dostupnost' tovara:
              - `deficient` — Defitsit
              - `actual` — Aktual'nyj
              - `balanced` — Balans
              - `nonActual` — Neaktual'nyj
              - `nonLiquid` — Nelikvid
              - `invalidData` — Ne rasschitano
             Example: ['deficient', 'balanced'].
        nm_i_ds (Union[Unset, List[int]]): Spisok artikulov WB dlja fil'tratsii Example: [111222333, 444555666].
        subject_id (Union[Unset, int]): ID predmeta Example: 123456.
        brand_name (Union[Unset, str]): Brend Example: Sportik.
        tag_id (Union[Unset, int]): ID jarlyka Example: 25345.
    """

    current_period: "PeriodSt"
    stock_type: StockType
    skip_deleted_nm: bool
    order_by: "TableOrderBy"
    availability_filters: List[AvailabilityFiltersItem]
    nm_i_ds: Union[Unset, List[int]] = UNSET
    subject_id: Union[Unset, int] = UNSET
    brand_name: Union[Unset, str] = UNSET
    tag_id: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current_period = self.current_period.to_dict()

        stock_type = self.stock_type.value

        skip_deleted_nm = self.skip_deleted_nm

        order_by = self.order_by.to_dict()

        availability_filters = []
        for componentsschemasavailability_filters_item_data in self.availability_filters:
            componentsschemasavailability_filters_item = componentsschemasavailability_filters_item_data.value
            availability_filters.append(componentsschemasavailability_filters_item)

        nm_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nm_i_ds, Unset):
            nm_i_ds = self.nm_i_ds

        subject_id = self.subject_id

        brand_name = self.brand_name

        tag_id = self.tag_id

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "currentPeriod": current_period,
                "stockType": stock_type,
                "skipDeletedNm": skip_deleted_nm,
                "orderBy": order_by,
                "availabilityFilters": availability_filters,
            }
        )
        if nm_i_ds is not UNSET:
            field_dict["nmIDs"] = nm_i_ds
        if subject_id is not UNSET:
            field_dict["subjectID"] = subject_id
        if brand_name is not UNSET:
            field_dict["brandName"] = brand_name
        if tag_id is not UNSET:
            field_dict["tagID"] = tag_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.period_st import PeriodSt
        from ..models.table_order_by import TableOrderBy

        d = src_dict.copy()
        current_period = PeriodSt.from_dict(d.pop("currentPeriod"))

        stock_type = StockType(d.pop("stockType"))

        skip_deleted_nm = d.pop("skipDeletedNm")

        order_by = TableOrderBy.from_dict(d.pop("orderBy"))

        availability_filters = []
        _availability_filters = d.pop("availabilityFilters")
        for componentsschemasavailability_filters_item_data in _availability_filters:
            componentsschemasavailability_filters_item = AvailabilityFiltersItem(
                componentsschemasavailability_filters_item_data
            )

            availability_filters.append(componentsschemasavailability_filters_item)

        nm_i_ds = cast(List[int], d.pop("nmIDs", UNSET))

        subject_id = d.pop("subjectID", UNSET)

        brand_name = d.pop("brandName", UNSET)

        tag_id = d.pop("tagID", UNSET)

        common_product_filters = cls(
            current_period=current_period,
            stock_type=stock_type,
            skip_deleted_nm=skip_deleted_nm,
            order_by=order_by,
            availability_filters=availability_filters,
            nm_i_ds=nm_i_ds,
            subject_id=subject_id,
            brand_name=brand_name,
            tag_id=tag_id,
        )

        common_product_filters.additional_properties = d
        return common_product_filters

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
