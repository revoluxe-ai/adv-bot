from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.table_product_item_add_to_cart import TableProductItemAddToCart
    from ..models.table_product_item_avg_position import TableProductItemAvgPosition
    from ..models.table_product_item_cart_to_order import TableProductItemCartToOrder
    from ..models.table_product_item_open_card import TableProductItemOpenCard
    from ..models.table_product_item_open_to_cart import TableProductItemOpenToCart
    from ..models.table_product_item_orders import TableProductItemOrders
    from ..models.table_product_item_price import TableProductItemPrice
    from ..models.table_product_item_visibility import TableProductItemVisibility


T = TypeVar("T", bound="TableProductItem")


@_attrs_define
class TableProductItem:
    """
    Attributes:
        nm_id (int): Artikul WB Example: 268913787.
        vendor_code (str): Artikul prodavtsa Example: wb3ha2668w.
        is_advertised (bool): Nahoditsja li tovar v prodvizhenii v Poiskovoj vydache
        is_card_rated (bool): Est' li rejting u kartochki tovara Example: True.
        rating (float): Rejting kartochki tovara Example: 6.
        feedback_rating (float): Rejting po otzyvam Example: 1.
        price (TableProductItemPrice): Tsena
        avg_position (TableProductItemAvgPosition): Srednjaja pozitsija tovara v rezul'tatah poiska
        open_card (TableProductItemOpenCard): Kolichestvo perehodov v kartochku tovara iz poiska
        add_to_cart (TableProductItemAddToCart): Skol'ko raz tovar iz poiska dobavili v korzinu
        open_to_cart (TableProductItemOpenToCart): Konversija v korzinu iz poiska — dolja dobavlenij tovara v korzinu po
            otnosheniju ko vsem perehodam v kartochku tovara iz poiska
        orders (TableProductItemOrders): Skol'ko raz tovary iz poiska zakazali
        cart_to_order (TableProductItemCartToOrder): Konversija v zakaz iz poiska — dolja zakazov tovara po otnosheniju
            ko vsem dobavlenijam tovara iz poiska v korzinu
        visibility (TableProductItemVisibility): Protsent vidimosti tovara v rezul'tatah poiska
        name (Union[Unset, str]): Nazvanie tovara Example: iPhone 13 256 GB Serebristyj.
        subject_name (Union[Unset, str]): Nazvanie predmeta Example: Smartfony.
        brand_name (Union[Unset, str]): Brend Example: Apple.
        main_photo (Union[Unset, str]): URL glavnogo foto kartochki tovara Example:
            https://basket-12.wbbasket.ru/vol1788/part178840/178840836/images/c246x328/1.webp.
        is_substituted_sku (Union[Unset, bool]): Iskali li tovar po podmennomu artikulu.<br>
            Pole budet v otvete pri nalichii v zaprose `includeSubstitutedSKUs` i/ili `includeSearchTexts`
             Example: True.
    """

    nm_id: int
    vendor_code: str
    is_advertised: bool
    is_card_rated: bool
    rating: float
    feedback_rating: float
    price: "TableProductItemPrice"
    avg_position: "TableProductItemAvgPosition"
    open_card: "TableProductItemOpenCard"
    add_to_cart: "TableProductItemAddToCart"
    open_to_cart: "TableProductItemOpenToCart"
    orders: "TableProductItemOrders"
    cart_to_order: "TableProductItemCartToOrder"
    visibility: "TableProductItemVisibility"
    name: Union[Unset, str] = UNSET
    subject_name: Union[Unset, str] = UNSET
    brand_name: Union[Unset, str] = UNSET
    main_photo: Union[Unset, str] = UNSET
    is_substituted_sku: Union[Unset, bool] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        vendor_code = self.vendor_code

        is_advertised = self.is_advertised

        is_card_rated = self.is_card_rated

        rating = self.rating

        feedback_rating = self.feedback_rating

        price = self.price.to_dict()

        avg_position = self.avg_position.to_dict()

        open_card = self.open_card.to_dict()

        add_to_cart = self.add_to_cart.to_dict()

        open_to_cart = self.open_to_cart.to_dict()

        orders = self.orders.to_dict()

        cart_to_order = self.cart_to_order.to_dict()

        visibility = self.visibility.to_dict()

        name = self.name

        subject_name = self.subject_name

        brand_name = self.brand_name

        main_photo = self.main_photo

        is_substituted_sku = self.is_substituted_sku

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmId": nm_id,
                "vendorCode": vendor_code,
                "isAdvertised": is_advertised,
                "isCardRated": is_card_rated,
                "rating": rating,
                "feedbackRating": feedback_rating,
                "price": price,
                "avgPosition": avg_position,
                "openCard": open_card,
                "addToCart": add_to_cart,
                "openToCart": open_to_cart,
                "orders": orders,
                "cartToOrder": cart_to_order,
                "visibility": visibility,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if brand_name is not UNSET:
            field_dict["brandName"] = brand_name
        if main_photo is not UNSET:
            field_dict["mainPhoto"] = main_photo
        if is_substituted_sku is not UNSET:
            field_dict["isSubstitutedSKU"] = is_substituted_sku

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_product_item_add_to_cart import TableProductItemAddToCart
        from ..models.table_product_item_avg_position import TableProductItemAvgPosition
        from ..models.table_product_item_cart_to_order import TableProductItemCartToOrder
        from ..models.table_product_item_open_card import TableProductItemOpenCard
        from ..models.table_product_item_open_to_cart import TableProductItemOpenToCart
        from ..models.table_product_item_orders import TableProductItemOrders
        from ..models.table_product_item_price import TableProductItemPrice
        from ..models.table_product_item_visibility import TableProductItemVisibility

        d = src_dict.copy()
        nm_id = d.pop("nmId")

        vendor_code = d.pop("vendorCode")

        is_advertised = d.pop("isAdvertised")

        is_card_rated = d.pop("isCardRated")

        rating = d.pop("rating")

        feedback_rating = d.pop("feedbackRating")

        price = TableProductItemPrice.from_dict(d.pop("price"))

        avg_position = TableProductItemAvgPosition.from_dict(d.pop("avgPosition"))

        open_card = TableProductItemOpenCard.from_dict(d.pop("openCard"))

        add_to_cart = TableProductItemAddToCart.from_dict(d.pop("addToCart"))

        open_to_cart = TableProductItemOpenToCart.from_dict(d.pop("openToCart"))

        orders = TableProductItemOrders.from_dict(d.pop("orders"))

        cart_to_order = TableProductItemCartToOrder.from_dict(d.pop("cartToOrder"))

        visibility = TableProductItemVisibility.from_dict(d.pop("visibility"))

        name = d.pop("name", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        brand_name = d.pop("brandName", UNSET)

        main_photo = d.pop("mainPhoto", UNSET)

        is_substituted_sku = d.pop("isSubstitutedSKU", UNSET)

        table_product_item = cls(
            nm_id=nm_id,
            vendor_code=vendor_code,
            is_advertised=is_advertised,
            is_card_rated=is_card_rated,
            rating=rating,
            feedback_rating=feedback_rating,
            price=price,
            avg_position=avg_position,
            open_card=open_card,
            add_to_cart=add_to_cart,
            open_to_cart=open_to_cart,
            orders=orders,
            cart_to_order=cart_to_order,
            visibility=visibility,
            name=name,
            subject_name=subject_name,
            brand_name=brand_name,
            main_photo=main_photo,
            is_substituted_sku=is_substituted_sku,
        )

        table_product_item.additional_properties = d
        return table_product_item

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
