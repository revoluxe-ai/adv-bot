from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.response_info_advert_params_item import ResponseInfoAdvertParamsItem


T = TypeVar("T", bound="ResponseInfoAdvert")


@_attrs_define
class ResponseInfoAdvert:
    """
    Attributes:
        end_time (Union[Unset, str]): Data zavershenija kampanii
        create_time (Union[Unset, str]): Vremja sozdanija kampanii Example: 2022-03-09T10:50:21.831623+03:00.
        change_time (Union[Unset, str]): Vremja poslednego izmenenija kampanii Example:
            2022-12-22T18:24:19.808701+03:00.
        start_time (Union[Unset, str]): Data poslednego zapuska kampanii
        name (Union[Unset, str]): Nazvanie kampanii
        params (Union[Unset, List['ResponseInfoAdvertParamsItem']]): Parametry kampanii
        daily_budget (Union[Unset, int]): Dnevnoj bjudzhet. Esli ne ustanovlen, to `0`
        advert_id (Union[Unset, int]): ID kampanii Example: 1234.
        status (Union[Unset, int]): Status kampanii:
            - `-1` — udalena, protsess udalenija budet zavershen v techenie 10 minut
            - `4` — gotova k zapusku
            - `7` — zavershena
            - `8` — otmenena
            - `9` — aktivna
            - `11` — na pauze
             Example: 9.
        type (Union[Unset, int]): Tip kampanii:
              - `4` — kampanija v kataloge (**ustarevshij tip**)
              - `5` — kampanija v kartochke tovara (**ustarevshij tip**)
              - `6` — kampanija v poiske (**ustarevshij tip**)
              - `7` — kampanija v rekomendatsijah na glavnoj stranitse (**ustarevshij tip**)
             Example: 4.
        payment_type (Union[Unset, str]): Model' oplaty:
            - `cpm` — za pokazy
        search_pluse_state (Union[Unset, bool]): Aktivnost' fiksirovannyh fraz:
              - `false` — ne aktivny
              - `true` — aktivny
    """

    end_time: Union[Unset, str] = UNSET
    create_time: Union[Unset, str] = UNSET
    change_time: Union[Unset, str] = UNSET
    start_time: Union[Unset, str] = UNSET
    name: Union[Unset, str] = UNSET
    params: Union[Unset, List["ResponseInfoAdvertParamsItem"]] = UNSET
    daily_budget: Union[Unset, int] = UNSET
    advert_id: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    type: Union[Unset, int] = UNSET
    payment_type: Union[Unset, str] = UNSET
    search_pluse_state: Union[Unset, bool] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        end_time = self.end_time

        create_time = self.create_time

        change_time = self.change_time

        start_time = self.start_time

        name = self.name

        params: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.params, Unset):
            params = []
            for params_item_data in self.params:
                params_item = params_item_data.to_dict()
                params.append(params_item)

        daily_budget = self.daily_budget

        advert_id = self.advert_id

        status = self.status

        type = self.type

        payment_type = self.payment_type

        search_pluse_state = self.search_pluse_state

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if end_time is not UNSET:
            field_dict["endTime"] = end_time
        if create_time is not UNSET:
            field_dict["createTime"] = create_time
        if change_time is not UNSET:
            field_dict["changeTime"] = change_time
        if start_time is not UNSET:
            field_dict["startTime"] = start_time
        if name is not UNSET:
            field_dict["name"] = name
        if params is not UNSET:
            field_dict["params"] = params
        if daily_budget is not UNSET:
            field_dict["dailyBudget"] = daily_budget
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if status is not UNSET:
            field_dict["status"] = status
        if type is not UNSET:
            field_dict["type"] = type
        if payment_type is not UNSET:
            field_dict["paymentType"] = payment_type
        if search_pluse_state is not UNSET:
            field_dict["searchPluseState"] = search_pluse_state

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.response_info_advert_params_item import ResponseInfoAdvertParamsItem

        d = src_dict.copy()
        end_time = d.pop("endTime", UNSET)

        create_time = d.pop("createTime", UNSET)

        change_time = d.pop("changeTime", UNSET)

        start_time = d.pop("startTime", UNSET)

        name = d.pop("name", UNSET)

        params = []
        _params = d.pop("params", UNSET)
        for params_item_data in _params or []:
            params_item = ResponseInfoAdvertParamsItem.from_dict(params_item_data)

            params.append(params_item)

        daily_budget = d.pop("dailyBudget", UNSET)

        advert_id = d.pop("advertId", UNSET)

        status = d.pop("status", UNSET)

        type = d.pop("type", UNSET)

        payment_type = d.pop("paymentType", UNSET)

        search_pluse_state = d.pop("searchPluseState", UNSET)

        response_info_advert = cls(
            end_time=end_time,
            create_time=create_time,
            change_time=change_time,
            start_time=start_time,
            name=name,
            params=params,
            daily_budget=daily_budget,
            advert_id=advert_id,
            status=status,
            type=type,
            payment_type=payment_type,
            search_pluse_state=search_pluse_state,
        )

        response_info_advert.additional_properties = d
        return response_info_advert

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
