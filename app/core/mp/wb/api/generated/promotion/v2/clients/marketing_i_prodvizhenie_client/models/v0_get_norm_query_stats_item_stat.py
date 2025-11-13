from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="V0GetNormQueryStatsItemStat")


@_attrs_define
class V0GetNormQueryStatsItemStat:
    """
    Attributes:
        norm_query (Union[Unset, str]): Poiskovyj klaster
        views (Union[Unset, int]): Kolichestvo prosmotrov
        clicks (Union[Unset, int]): Kolichestvo klikov
        atbs (Union[Unset, int]): Kolichestvo dobavlenij tovarov v korzinu
        orders (Union[Unset, int]): Kolichestvo zakazov
        ctr (Union[Unset, float]): Klikabel'nost' — otnoshenie chisla klikov k kolichestvu pokazov, %
        cpc (Union[Unset, float]): Stoimost' odnogo klika, ₽
        cpm (Union[Unset, float]): Srednjaja stoimost' za tysjachu pokazov, ₽
        avg_pos (Union[Unset, float]): Srednjaja pozitsija tovara na stranitsah poiskovoj vydachi
    """

    norm_query: Union[Unset, str] = UNSET
    views: Union[Unset, int] = UNSET
    clicks: Union[Unset, int] = UNSET
    atbs: Union[Unset, int] = UNSET
    orders: Union[Unset, int] = UNSET
    ctr: Union[Unset, float] = UNSET
    cpc: Union[Unset, float] = UNSET
    cpm: Union[Unset, float] = UNSET
    avg_pos: Union[Unset, float] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        norm_query = self.norm_query

        views = self.views

        clicks = self.clicks

        atbs = self.atbs

        orders = self.orders

        ctr = self.ctr

        cpc = self.cpc

        cpm = self.cpm

        avg_pos = self.avg_pos

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if norm_query is not UNSET:
            field_dict["norm_query"] = norm_query
        if views is not UNSET:
            field_dict["views"] = views
        if clicks is not UNSET:
            field_dict["clicks"] = clicks
        if atbs is not UNSET:
            field_dict["atbs"] = atbs
        if orders is not UNSET:
            field_dict["orders"] = orders
        if ctr is not UNSET:
            field_dict["ctr"] = ctr
        if cpc is not UNSET:
            field_dict["cpc"] = cpc
        if cpm is not UNSET:
            field_dict["cpm"] = cpm
        if avg_pos is not UNSET:
            field_dict["avg_pos"] = avg_pos

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        norm_query = d.pop("norm_query", UNSET)

        views = d.pop("views", UNSET)

        clicks = d.pop("clicks", UNSET)

        atbs = d.pop("atbs", UNSET)

        orders = d.pop("orders", UNSET)

        ctr = d.pop("ctr", UNSET)

        cpc = d.pop("cpc", UNSET)

        cpm = d.pop("cpm", UNSET)

        avg_pos = d.pop("avg_pos", UNSET)

        v0_get_norm_query_stats_item_stat = cls(
            norm_query=norm_query,
            views=views,
            clicks=clicks,
            atbs=atbs,
            orders=orders,
            ctr=ctr,
            cpc=cpc,
            cpm=cpm,
            avg_pos=avg_pos,
        )

        v0_get_norm_query_stats_item_stat.additional_properties = d
        return v0_get_norm_query_stats_item_stat

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
