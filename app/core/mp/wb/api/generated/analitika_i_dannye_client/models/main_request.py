from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.position_cluster import PositionCluster
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.order_by import OrderBy
    from ..models.past_period import PastPeriod
    from ..models.period import Period


T = TypeVar("T", bound="MainRequest")


@_attrs_define
class MainRequest:
    """Parametry zaprosa dlja formirovanija glavnoj stranitsy:
    - `currentPeriod` — tekuschij period
    - `pastPeriod` — predyduschij period dlja sravnenija

      Attributes:
          current_period (Period): Tekuschij period
          position_cluster (PositionCluster): Tovary s kakoj srednej pozitsiej v poiske pokazyvat' v otchete:
                - `all` — vse
                - `firstHundred` — ot 1 do 100
                - `secondHundred` — ot 101 do 200
                - `below` — ot 201 i nizhe
               Example: all.
          order_by (OrderBy): Parametry sortirovki
          limit (int): Kolichestvo grupp tovarov v otvete Example: 130.
          offset (int): Posle kakogo elementa vydavat' dannye Example: 50.
          past_period (Union[Unset, PastPeriod]): Proshlyj period dlja sravnenija. Kolichestvo dnej — men'she ili ravno
              `currentPeriod`
          nm_ids (Union[Unset, List[int]]): Spisok artikulov WB dlja fil'tratsii Example: [162579635, 166699779].
          subject_ids (Union[Unset, List[int]]): Spisok ID predmetov dlja fil'tratsii Example: [32, 64].
          brand_names (Union[Unset, List[str]]): Spisok brendov dlja fil'tratsii Example: ['Adidas', 'Nike'].
          tag_ids (Union[Unset, List[int]]): Spisok ID jarlykov dlja fil'tratsii Example: [3, 5, 6].
          include_substituted_sk_us (Union[Unset, bool]): Pokazat' dannye po prjamym zaprosam s [podmennym
              artikulom](https://seller.wildberries.ru/help-center/article/A-524) Default: True. Example: True.
          include_search_texts (Union[Unset, bool]): Pokazat' dannye po poiskovym zaprosam bez ucheta podmennogo artikula
              Default: True.
    """

    current_period: "Period"
    position_cluster: PositionCluster
    order_by: "OrderBy"
    limit: int
    offset: int
    past_period: Union[Unset, "PastPeriod"] = UNSET
    nm_ids: Union[Unset, List[int]] = UNSET
    subject_ids: Union[Unset, List[int]] = UNSET
    brand_names: Union[Unset, List[str]] = UNSET
    tag_ids: Union[Unset, List[int]] = UNSET
    include_substituted_sk_us: Union[Unset, bool] = True
    include_search_texts: Union[Unset, bool] = True
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current_period = self.current_period.to_dict()

        position_cluster = self.position_cluster.value

        order_by = self.order_by.to_dict()

        limit = self.limit

        offset = self.offset

        past_period: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.past_period, Unset):
            past_period = self.past_period.to_dict()

        nm_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nm_ids, Unset):
            nm_ids = self.nm_ids

        subject_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.subject_ids, Unset):
            subject_ids = self.subject_ids

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
                "positionCluster": position_cluster,
                "orderBy": order_by,
                "limit": limit,
                "offset": offset,
            }
        )
        if past_period is not UNSET:
            field_dict["pastPeriod"] = past_period
        if nm_ids is not UNSET:
            field_dict["nmIds"] = nm_ids
        if subject_ids is not UNSET:
            field_dict["subjectIds"] = subject_ids
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
        from ..models.order_by import OrderBy
        from ..models.past_period import PastPeriod
        from ..models.period import Period

        d = src_dict.copy()
        current_period = Period.from_dict(d.pop("currentPeriod"))

        position_cluster = PositionCluster(d.pop("positionCluster"))

        order_by = OrderBy.from_dict(d.pop("orderBy"))

        limit = d.pop("limit")

        offset = d.pop("offset")

        _past_period = d.pop("pastPeriod", UNSET)
        past_period: Union[Unset, PastPeriod]
        if isinstance(_past_period, Unset):
            past_period = UNSET
        else:
            past_period = PastPeriod.from_dict(_past_period)

        nm_ids = cast(List[int], d.pop("nmIds", UNSET))

        subject_ids = cast(List[int], d.pop("subjectIds", UNSET))

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        tag_ids = cast(List[int], d.pop("tagIds", UNSET))

        include_substituted_sk_us = d.pop("includeSubstitutedSKUs", UNSET)

        include_search_texts = d.pop("includeSearchTexts", UNSET)

        main_request = cls(
            current_period=current_period,
            position_cluster=position_cluster,
            order_by=order_by,
            limit=limit,
            offset=offset,
            past_period=past_period,
            nm_ids=nm_ids,
            subject_ids=subject_ids,
            brand_names=brand_names,
            tag_ids=tag_ids,
            include_substituted_sk_us=include_substituted_sk_us,
            include_search_texts=include_search_texts,
        )

        main_request.additional_properties = d
        return main_request

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
