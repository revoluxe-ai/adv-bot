from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.position_cluster import PositionCluster
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.order_by_gr_te import OrderByGrTe
    from ..models.past_period import PastPeriod
    from ..models.period import Period


T = TypeVar("T", bound="SearchReportGroupReqParams")


@_attrs_define
class SearchReportGroupReqParams:
    """Parametry otcheta

    Attributes:
        current_period (Period): Tekuschij period
        subject_ids (List[int]): Spisok ID predmetov dlja fil'tratsii. Ostav'te pustym, chtoby poluchit' otchet po vsem
            predmetam Example: [64, 334].
        order_by (OrderByGrTe): Parametry sortirovki
        position_cluster (PositionCluster): Tovary s kakoj srednej pozitsiej v poiske pokazyvat' v otchete:
              - `all` — vse
              - `firstHundred` — ot 1 do 100
              - `secondHundred` — ot 101 do 200
              - `below` — ot 201 i nizhe
             Example: all.
        past_period (Union[Unset, PastPeriod]): Proshlyj period dlja sravnenija. Kolichestvo dnej — men'she ili ravno
            `currentPeriod`
        nm_ids (Union[Unset, List[int]]): Artikuly WB, po kotorym sostavit' otchet. Ostav'te pustym, chtoby poluchit'
            otchet obo vseh tovarah
        brand_names (Union[Unset, List[str]]): Spisok brendov dlja fil'tratsii Example: ['nike', 'adidas'].
        tag_ids (Union[Unset, List[int]]): Spisok ID jarlykov dlja fil'tratsii Example: [32, 53].
        include_substituted_sk_us (Union[Unset, bool]): Pokazat' dannye po prjamym zaprosam s [podmennym
            artikulom](https://seller.wildberries.ru/help-center/article/A-524) Default: True. Example: True.
        include_search_texts (Union[Unset, bool]): Pokazat' dannye po poiskovym zaprosam bez ucheta podmennogo artikula
            Default: True.
    """

    current_period: "Period"
    subject_ids: List[int]
    order_by: "OrderByGrTe"
    position_cluster: PositionCluster
    past_period: Union[Unset, "PastPeriod"] = UNSET
    nm_ids: Union[Unset, List[int]] = UNSET
    brand_names: Union[Unset, List[str]] = UNSET
    tag_ids: Union[Unset, List[int]] = UNSET
    include_substituted_sk_us: Union[Unset, bool] = True
    include_search_texts: Union[Unset, bool] = True
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current_period = self.current_period.to_dict()

        subject_ids = self.subject_ids

        order_by = self.order_by.to_dict()

        position_cluster = self.position_cluster.value

        past_period: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.past_period, Unset):
            past_period = self.past_period.to_dict()

        nm_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nm_ids, Unset):
            nm_ids = self.nm_ids

        brand_names: Union[Unset, List[str]] = UNSET
        if not isinstance(self.brand_names, Unset):
            brand_names = self.brand_names

        tag_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.tag_ids, Unset):
            tag_ids = self.tag_ids

        include_substituted_sk_us = self.include_substituted_sk_us

        include_search_texts = self.include_search_texts

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "currentPeriod": current_period,
                "subjectIds": subject_ids,
                "orderBy": order_by,
                "positionCluster": position_cluster,
            }
        )
        if past_period is not UNSET:
            field_dict["pastPeriod"] = past_period
        if nm_ids is not UNSET:
            field_dict["nmIds"] = nm_ids
        if brand_names is not UNSET:
            field_dict["brandNames"] = brand_names
        if tag_ids is not UNSET:
            field_dict["tagIds"] = tag_ids
        if include_substituted_sk_us is not UNSET:
            field_dict["includeSubstitutedSKUs"] = include_substituted_sk_us
        if include_search_texts is not UNSET:
            field_dict["includeSearchTexts"] = include_search_texts

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.order_by_gr_te import OrderByGrTe
        from ..models.past_period import PastPeriod
        from ..models.period import Period

        d = src_dict.copy()
        current_period = Period.from_dict(d.pop("currentPeriod"))

        subject_ids = cast(List[int], d.pop("subjectIds"))

        order_by = OrderByGrTe.from_dict(d.pop("orderBy"))

        position_cluster = PositionCluster(d.pop("positionCluster"))

        _past_period = d.pop("pastPeriod", UNSET)
        past_period: Union[Unset, PastPeriod]
        if isinstance(_past_period, Unset):
            past_period = UNSET
        else:
            past_period = PastPeriod.from_dict(_past_period)

        nm_ids = cast(List[int], d.pop("nmIds", UNSET))

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        tag_ids = cast(List[int], d.pop("tagIds", UNSET))

        include_substituted_sk_us = d.pop("includeSubstitutedSKUs", UNSET)

        include_search_texts = d.pop("includeSearchTexts", UNSET)

        search_report_group_req_params = cls(
            current_period=current_period,
            subject_ids=subject_ids,
            order_by=order_by,
            position_cluster=position_cluster,
            past_period=past_period,
            nm_ids=nm_ids,
            brand_names=brand_names,
            tag_ids=tag_ids,
            include_substituted_sk_us=include_substituted_sk_us,
            include_search_texts=include_search_texts,
        )

        search_report_group_req_params.additional_properties = d
        return search_report_group_req_params

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
