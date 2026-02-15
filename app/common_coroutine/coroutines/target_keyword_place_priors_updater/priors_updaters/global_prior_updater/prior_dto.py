import attrs


@attrs.define
class PriorDTO:
    conv_cart_on_views: float = attrs.field(
        validator=attrs.validators.and_(
            attrs.validators.gt(0.0),   # > 0
            attrs.validators.le(1.0),   # <= 1
        )
    )


    @property
    def prior_carts(self) -> int:
        return 1

    @property
    def prior_views(self) -> int:
        views_for_one_cart = self.prior_carts/self.conv_cart_on_views
        if views_for_one_cart <= 0:
            raise ValueError()

        return int(round(1/self.conv_cart_on_views, 0))
