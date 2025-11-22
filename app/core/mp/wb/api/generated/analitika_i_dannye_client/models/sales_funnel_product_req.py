from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.sales_funnel_product_req_params import SalesFunnelProductReqParams


T = TypeVar("T", bound="SalesFunnelProductReq")


@_attrs_define
class SalesFunnelProductReq:
    """
    Attributes:
        id (str): ID otcheta v UUID-formate. Generiruetsja prodavtsom samostojatel'no
        report_type (str): Tip otcheta `DETAIL_HISTORY_REPORT` — Voronka prodazh. Po artikulam WB
        params (SalesFunnelProductReqParams): Parametry otcheta
        user_report_name (Union[Unset, str]): Nazvanie otcheta. Esli ne ukazano, sformiruetsja avtomaticheski
    """

    id: str
    report_type: str
    params: "SalesFunnelProductReqParams"
    user_report_name: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        report_type = self.report_type

        params = self.params.to_dict()

        user_report_name = self.user_report_name

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "reportType": report_type,
                "params": params,
            }
        )
        if user_report_name is not UNSET:
            field_dict["userReportName"] = user_report_name

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.sales_funnel_product_req_params import SalesFunnelProductReqParams

        d = src_dict.copy()
        id = d.pop("id")

        report_type = d.pop("reportType")

        params = SalesFunnelProductReqParams.from_dict(d.pop("params"))

        user_report_name = d.pop("userReportName", UNSET)

        sales_funnel_product_req = cls(
            id=id,
            report_type=report_type,
            params=params,
            user_report_name=user_report_name,
        )

        sales_funnel_product_req.additional_properties = d
        return sales_funnel_product_req

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
