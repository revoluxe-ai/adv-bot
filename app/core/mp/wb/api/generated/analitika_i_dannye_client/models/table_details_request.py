from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.table_details_request_position_cluster import TableDetailsRequestPositionCluster
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.order_by import OrderBy
    from ..models.past_period import PastPeriod
    from ..models.period import Period


T = TypeVar("T", bound="TableDetailsRequest")


@_attrs_define
class TableDetailsRequest:
    """Parametry zaprosa dlja paginatsii po tovaram v gruppe:
    - `currentPeriod` — tekuschij period
    - `pastPeriod` — predyduschij period dlja sravnenija

      Attributes:
          current_period (Period): Tekuschij period
          order_by (OrderBy): Parametry sortirovki
          position_cluster (TableDetailsRequestPositionCluster): Tovary s kakoj srednej pozitsiej v poiske pokazyvat' v
              otchete:
                - `all` — vse
                - `firstHundred` — ot 1 do 100
                - `secondHundred` — ot 101 do 200
                - `below` — ot 201 i nizhe
          limit (int): Kolichestvo tovarov v otvete Example: 150.
          offset (int): Posle kakogo elementa vydavat' dannye Example: 100.
          past_period (Union[Unset, PastPeriod]): Proshlyj period dlja sravnenija. Kolichestvo dnej — men'she ili ravno
              `currentPeriod`
          subject_id (Union[Unset, int]): ID predmeta Example: 123.
          brand_name (Union[Unset, str]): Nazvanie tovara Example: Apple.
          tag_id (Union[Unset, int]): ID jarlyka Example: 45.
          nm_ids (Union[Unset, List[int]]): Spisok artikulov WB Example: [162579635, 166699779].
          include_substituted_sk_us (Union[Unset, bool]): Pokazat' dannye po prjamym zaprosam s [podmennym
              artikulom](https://seller.wildberries.ru/help-center/article/A-524) Default: True. Example: True.
          include_search_texts (Union[Unset, bool]): Pokazat' dannye po poiskovym zaprosam bez ucheta podmennogo artikula
              Default: True.
    """

    current_period: "Period"
    order_by: "OrderBy"
    position_cluster: TableDetailsRequestPositionCluster
    limit: int
    offset: int
    past_period: Union[Unset, "PastPeriod"] = UNSET
    subject_id: Union[Unset, int] = UNSET
    brand_name: Union[Unset, str] = UNSET
    tag_id: Union[Unset, int] = UNSET
    nm_ids: Union[Unset, List[int]] = UNSET
    include_substituted_sk_us: Union[Unset, bool] = True
    include_search_texts: Union[Unset, bool] = True
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current_period = self.current_period.to_dict()

        order_by = self.order_by.to_dict()

        position_cluster = self.position_cluster.value

        limit = self.limit

        offset = self.offset

        past_period: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.past_period, Unset):
            past_period = self.past_period.to_dict()

        subject_id = self.subject_id

        brand_name = self.brand_name

        tag_id = self.tag_id

        nm_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nm_ids, Unset):
            nm_ids = self.nm_ids

        include_substituted_sk_us = self.include_substituted_sk_us

        include_search_texts = self.include_search_texts

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "currentPeriod": current_period,
                "orderBy": order_by,
                "positionCluster": position_cluster,
                "limit": limit,
                "offset": offset,
            }
        )
        if past_period is not UNSET:
            field_dict["pastPeriod"] = past_period
        if subject_id is not UNSET:
            field_dict["subjectId"] = subject_id
        if brand_name is not UNSET:
            field_dict["brandName"] = brand_name
        if tag_id is not UNSET:
            field_dict["tagId"] = tag_id
        if nm_ids is not UNSET:
            field_dict["nmIds"] = nm_ids
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

        order_by = OrderBy.from_dict(d.pop("orderBy"))

        position_cluster = TableDetailsRequestPositionCluster(d.pop("positionCluster"))

        limit = d.pop("limit")

        offset = d.pop("offset")

        _past_period = d.pop("pastPeriod", UNSET)
        past_period: Union[Unset, PastPeriod]
        if isinstance(_past_period, Unset):
            past_period = UNSET
        else:
            past_period = PastPeriod.from_dict(_past_period)

        subject_id = d.pop("subjectId", UNSET)

        brand_name = d.pop("brandName", UNSET)

        tag_id = d.pop("tagId", UNSET)

        nm_ids = cast(List[int], d.pop("nmIds", UNSET))

        include_substituted_sk_us = d.pop("includeSubstitutedSKUs", UNSET)

        include_search_texts = d.pop("includeSearchTexts", UNSET)

        table_details_request = cls(
            current_period=current_period,
            order_by=order_by,
            position_cluster=position_cluster,
            limit=limit,
            offset=offset,
            past_period=past_period,
            subject_id=subject_id,
            brand_name=brand_name,
            tag_id=tag_id,
            nm_ids=nm_ids,
            include_substituted_sk_us=include_substituted_sk_us,
            include_search_texts=include_search_texts,
        )

        table_details_request.additional_properties = d
        return table_details_request

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
