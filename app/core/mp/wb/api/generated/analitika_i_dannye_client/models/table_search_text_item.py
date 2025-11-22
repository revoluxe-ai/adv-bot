from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_search_text_item_add_to_cart import TableSearchTextItemAddToCart
    from ..models.table_search_text_item_avg_position import TableSearchTextItemAvgPosition
    from ..models.table_search_text_item_cart_to_order import TableSearchTextItemCartToOrder
    from ..models.table_search_text_item_frequency import TableSearchTextItemFrequency
    from ..models.table_search_text_item_median_position import TableSearchTextItemMedianPosition
    from ..models.table_search_text_item_open_card import TableSearchTextItemOpenCard
    from ..models.table_search_text_item_open_to_cart import TableSearchTextItemOpenToCart
    from ..models.table_search_text_item_orders import TableSearchTextItemOrders
    from ..models.table_search_text_item_price import TableSearchTextItemPrice
    from ..models.table_search_text_item_visibility import TableSearchTextItemVisibility


T = TypeVar("T", bound="TableSearchTextItem")


@_attrs_define
class TableSearchTextItem:
    """
    Attributes:
        text (str): Tekst poiskovogo zaprosa Example: kostjum.
        nm_id (int): Artikul WB Example: 211131895.
        subject_name (str): Nazvanie predmeta Example: Phones.
        brand_name (str): Brend Example: Apple.
        vendor_code (str): Artikul prodavtsa Example: wb3ha2668w.
        name (str): Nazvanie tovara Example: iPhone 13 256 GB Serebristyj.
        is_card_rated (bool): Est' li rejting u kartochki tovara Example: True.
        rating (float): Rejting kartochki tovara Example: 6.
        feedback_rating (float): Rejting po otzyvam Example: 1.
        price (TableSearchTextItemPrice): Tsena
        frequency (TableSearchTextItemFrequency): Kolichestvo obraschenij s poiskovym zaprosom
        week_frequency (int): Kolichestvo obraschenij s poiskovym zaprosom za nedelju Example: 140.
        median_position (TableSearchTextItemMedianPosition): Mediannaja pozitsija. Uchityvajutsja tol'ko te pozitsii, iz
            kotoryh pol'zovateli dobavljali tovar v korzinu ili perehodili v ego kartochku. Seredinnoe znachenie pozitsii v
            poiskovoj vydache, kotoroe iskljuchaet sil'nye otklonenija dannyh ot srednego znachenija
        avg_position (TableSearchTextItemAvgPosition): Srednjaja pozitsija tovara v rezul'tatah poiska
        open_card (TableSearchTextItemOpenCard): Kolichestvo perehodov v kartochku tovara iz poiska
        add_to_cart (TableSearchTextItemAddToCart): Skol'ko raz tovar iz poiska dobavili v korzinu
        open_to_cart (TableSearchTextItemOpenToCart): Konversija v korzinu iz poiska — dolja dobavlenij tovara v korzinu
            po otnosheniju ko vsem perehodam v kartochku tovara iz poiska
        orders (TableSearchTextItemOrders): Skol'ko raz tovary iz poiska zakazali
        cart_to_order (TableSearchTextItemCartToOrder): Konversija v zakaz iz poiska — dolja zakazov tovara po
            otnosheniju ko vsem dobavlenijam tovara iz poiska v korzinu
        visibility (TableSearchTextItemVisibility): Protsent vidimosti tovara v rezul'tatah poiska
    """

    text: str
    nm_id: int
    subject_name: str
    brand_name: str
    vendor_code: str
    name: str
    is_card_rated: bool
    rating: float
    feedback_rating: float
    price: "TableSearchTextItemPrice"
    frequency: "TableSearchTextItemFrequency"
    week_frequency: int
    median_position: "TableSearchTextItemMedianPosition"
    avg_position: "TableSearchTextItemAvgPosition"
    open_card: "TableSearchTextItemOpenCard"
    add_to_cart: "TableSearchTextItemAddToCart"
    open_to_cart: "TableSearchTextItemOpenToCart"
    orders: "TableSearchTextItemOrders"
    cart_to_order: "TableSearchTextItemCartToOrder"
    visibility: "TableSearchTextItemVisibility"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        text = self.text

        nm_id = self.nm_id

        subject_name = self.subject_name

        brand_name = self.brand_name

        vendor_code = self.vendor_code

        name = self.name

        is_card_rated = self.is_card_rated

        rating = self.rating

        feedback_rating = self.feedback_rating

        price = self.price.to_dict()

        frequency = self.frequency.to_dict()

        week_frequency = self.week_frequency

        median_position = self.median_position.to_dict()

        avg_position = self.avg_position.to_dict()

        open_card = self.open_card.to_dict()

        add_to_cart = self.add_to_cart.to_dict()

        open_to_cart = self.open_to_cart.to_dict()

        orders = self.orders.to_dict()

        cart_to_order = self.cart_to_order.to_dict()

        visibility = self.visibility.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "text": text,
                "nmId": nm_id,
                "subjectName": subject_name,
                "brandName": brand_name,
                "vendorCode": vendor_code,
                "name": name,
                "isCardRated": is_card_rated,
                "rating": rating,
                "feedbackRating": feedback_rating,
                "price": price,
                "frequency": frequency,
                "weekFrequency": week_frequency,
                "medianPosition": median_position,
                "avgPosition": avg_position,
                "openCard": open_card,
                "addToCart": add_to_cart,
                "openToCart": open_to_cart,
                "orders": orders,
                "cartToOrder": cart_to_order,
                "visibility": visibility,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_search_text_item_add_to_cart import TableSearchTextItemAddToCart
        from ..models.table_search_text_item_avg_position import TableSearchTextItemAvgPosition
        from ..models.table_search_text_item_cart_to_order import TableSearchTextItemCartToOrder
        from ..models.table_search_text_item_frequency import TableSearchTextItemFrequency
        from ..models.table_search_text_item_median_position import TableSearchTextItemMedianPosition
        from ..models.table_search_text_item_open_card import TableSearchTextItemOpenCard
        from ..models.table_search_text_item_open_to_cart import TableSearchTextItemOpenToCart
        from ..models.table_search_text_item_orders import TableSearchTextItemOrders
        from ..models.table_search_text_item_price import TableSearchTextItemPrice
        from ..models.table_search_text_item_visibility import TableSearchTextItemVisibility

        d = src_dict.copy()
        text = d.pop("text")

        nm_id = d.pop("nmId")

        subject_name = d.pop("subjectName")

        brand_name = d.pop("brandName")

        vendor_code = d.pop("vendorCode")

        name = d.pop("name")

        is_card_rated = d.pop("isCardRated")

        rating = d.pop("rating")

        feedback_rating = d.pop("feedbackRating")

        price = TableSearchTextItemPrice.from_dict(d.pop("price"))

        frequency = TableSearchTextItemFrequency.from_dict(d.pop("frequency"))

        week_frequency = d.pop("weekFrequency")

        median_position = TableSearchTextItemMedianPosition.from_dict(d.pop("medianPosition"))

        avg_position = TableSearchTextItemAvgPosition.from_dict(d.pop("avgPosition"))

        open_card = TableSearchTextItemOpenCard.from_dict(d.pop("openCard"))

        add_to_cart = TableSearchTextItemAddToCart.from_dict(d.pop("addToCart"))

        open_to_cart = TableSearchTextItemOpenToCart.from_dict(d.pop("openToCart"))

        orders = TableSearchTextItemOrders.from_dict(d.pop("orders"))

        cart_to_order = TableSearchTextItemCartToOrder.from_dict(d.pop("cartToOrder"))

        visibility = TableSearchTextItemVisibility.from_dict(d.pop("visibility"))

        table_search_text_item = cls(
            text=text,
            nm_id=nm_id,
            subject_name=subject_name,
            brand_name=brand_name,
            vendor_code=vendor_code,
            name=name,
            is_card_rated=is_card_rated,
            rating=rating,
            feedback_rating=feedback_rating,
            price=price,
            frequency=frequency,
            week_frequency=week_frequency,
            median_position=median_position,
            avg_position=avg_position,
            open_card=open_card,
            add_to_cart=add_to_cart,
            open_to_cart=open_to_cart,
            orders=orders,
            cart_to_order=cart_to_order,
            visibility=visibility,
        )

        table_search_text_item.additional_properties = d
        return table_search_text_item

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
