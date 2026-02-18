from dataclasses import dataclass


@dataclass
class ConvCartToViewsOnPosition:
    keyword: str
    position: int
    conv_cart_to_views: float
