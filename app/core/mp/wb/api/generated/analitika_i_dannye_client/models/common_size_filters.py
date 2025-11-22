from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.stock_type import StockType

if TYPE_CHECKING:
    from ..models.period_st import PeriodSt
    from ..models.table_order_by import TableOrderBy


T = TypeVar("T", bound="CommonSizeFilters")


@_attrs_define
class CommonSizeFilters:
    """Obschie fil'try po razmeru

    Attributes:
        nm_id (int): Artikul WB Example: 123456789.
        current_period (PeriodSt): Period
        stock_type (StockType): Tip skladov hranenija tovarov:
              - `""` — vse
              - `wb` — Sklady WB
              - `mp` — Sklady Marketplejs (FBS)
             Example: mp.
        order_by (TableOrderBy): Vid sortirovki dannyh
        include_office (bool): Vkljuchit' detalizatsiju po skladam Example: True.
    """

    nm_id: int
    current_period: "PeriodSt"
    stock_type: StockType
    order_by: "TableOrderBy"
    include_office: bool
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        current_period = self.current_period.to_dict()

        stock_type = self.stock_type.value

        order_by = self.order_by.to_dict()

        include_office = self.include_office

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmID": nm_id,
                "currentPeriod": current_period,
                "stockType": stock_type,
                "orderBy": order_by,
                "includeOffice": include_office,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.period_st import PeriodSt
        from ..models.table_order_by import TableOrderBy

        d = src_dict.copy()
        nm_id = d.pop("nmID")

        current_period = PeriodSt.from_dict(d.pop("currentPeriod"))

        stock_type = StockType(d.pop("stockType"))

        order_by = TableOrderBy.from_dict(d.pop("orderBy"))

        include_office = d.pop("includeOffice")

        common_size_filters = cls(
            nm_id=nm_id,
            current_period=current_period,
            stock_type=stock_type,
            order_by=order_by,
            include_office=include_office,
        )

        common_size_filters.additional_properties = d
        return common_size_filters

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
