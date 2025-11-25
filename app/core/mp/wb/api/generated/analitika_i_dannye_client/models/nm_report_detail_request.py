from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_request_order_by import NmReportDetailRequestOrderBy
    from ..models.nm_report_detail_request_period import NmReportDetailRequestPeriod


T = TypeVar("T", bound="NmReportDetailRequest")


@_attrs_define
class NmReportDetailRequest:
    """
    Attributes:
        period (NmReportDetailRequestPeriod): Period
        page (int): Stranitsa Example: 1.
        brand_names (Union[Unset, List[str]]): Brendy
        object_i_ds (Union[Unset, List[int]]): ID predmetov
        tag_i_ds (Union[Unset, List[int]]): ID jarlykov
        nm_i_ds (Union[Unset, List[int]]): Artikuly WB
        timezone (Union[Unset, str]): Vremennaja zona.<br> Esli ne ukazano, to po umolchaniju ispol'zuetsja
            Europe/Moscow.
             Example: Europe/Moscow.
        order_by (Union[Unset, NmReportDetailRequestOrderBy]): Parametry sortirovki.
            Esli ne ukazano, to po umolchaniju ispol'zuetsja znachenie "openCard" i sortirovka po ubyvaniju.

            Vse vidy sortirovki `field`:
            - `openCard` — po otkrytiju kartochki (perehod na stranitsu tovara)
            - `addToCart` — po dobavlenijam v korzinu
            - `orders` — po kol-vu zakazov
            - `avgRubPrice` — po srednej tsene v rubljah
            - `ordersSumRub` — po summe zakazov v rubljah
            - `stockMpQty` — po kol-vu ostatkov marketplejsa sht.
            - `stockWbQty` — po kol-vu ostatkov na sklade sht.
            - `cancelSumRub` — summe vozvratov v rubljah
            - `cancelCount` — po kol-vu vozvratov
            - `buyoutCount` — po kol-vu vykupov
            - `buyoutSumRub` — po summe vykupov
    """

    period: "NmReportDetailRequestPeriod"
    page: int
    brand_names: Union[Unset, List[str]] = UNSET
    object_i_ds: Union[Unset, List[int]] = UNSET
    tag_i_ds: Union[Unset, List[int]] = UNSET
    nm_i_ds: Union[Unset, List[int]] = UNSET
    timezone: Union[Unset, str] = UNSET
    order_by: Union[Unset, "NmReportDetailRequestOrderBy"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        period = self.period.to_dict()

        page = self.page

        brand_names: Union[Unset, List[str]] = UNSET
        if not isinstance(self.brand_names, Unset):
            brand_names = self.brand_names

        object_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.object_i_ds, Unset):
            object_i_ds = self.object_i_ds

        tag_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.tag_i_ds, Unset):
            tag_i_ds = self.tag_i_ds

        nm_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nm_i_ds, Unset):
            nm_i_ds = self.nm_i_ds

        timezone = self.timezone

        order_by: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.order_by, Unset):
            order_by = self.order_by.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "period": period,
                "page": page,
            }
        )
        if brand_names is not UNSET:
            field_dict["brandNames"] = brand_names
        if object_i_ds is not UNSET:
            field_dict["objectIDs"] = object_i_ds
        if tag_i_ds is not UNSET:
            field_dict["tagIDs"] = tag_i_ds
        if nm_i_ds is not UNSET:
            field_dict["nmIDs"] = nm_i_ds
        if timezone is not UNSET:
            field_dict["timezone"] = timezone
        if order_by is not UNSET:
            field_dict["orderBy"] = order_by

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_request_order_by import NmReportDetailRequestOrderBy
        from ..models.nm_report_detail_request_period import NmReportDetailRequestPeriod

        d = src_dict.copy()
        period = NmReportDetailRequestPeriod.from_dict(d.pop("period"))

        page = d.pop("page")

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        object_i_ds = cast(List[int], d.pop("objectIDs", UNSET))

        tag_i_ds = cast(List[int], d.pop("tagIDs", UNSET))

        nm_i_ds = cast(List[int], d.pop("nmIDs", UNSET))

        timezone = d.pop("timezone", UNSET)

        _order_by = d.pop("orderBy", UNSET)
        order_by: Union[Unset, NmReportDetailRequestOrderBy]
        if isinstance(_order_by, Unset):
            order_by = UNSET
        else:
            order_by = NmReportDetailRequestOrderBy.from_dict(_order_by)

        nm_report_detail_request = cls(
            period=period,
            page=page,
            brand_names=brand_names,
            object_i_ds=object_i_ds,
            tag_i_ds=tag_i_ds,
            nm_i_ds=nm_i_ds,
            timezone=timezone,
            order_by=order_by,
        )

        nm_report_detail_request.additional_properties = d
        return nm_report_detail_request

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
