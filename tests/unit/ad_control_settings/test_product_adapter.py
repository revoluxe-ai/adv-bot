"""Product DrrProfile adapter boundary."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.product_adapter import (
    ProductDrrPolicyAdapter,
    ProductDrrPolicyAdapterSuccess,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.product_control.domain.effective_control_resolver import (
    EffectiveControlInput,
    EffectiveControlResolver,
)
from app.modules.product_control.domain.enums import (
    ProductControlMode,
    ShopControlEnrollment,
)


@pytest.mark.unit
def test_product_adapter_maps_active_profile() -> None:
    profile = drr_profile_from_percent(Decimal(12), Decimal(18))
    effective = EffectiveControlResolver.resolve(
        EffectiveControlInput(
            shop_enrollment=ShopControlEnrollment.ENROLLED,
            product_mode=ProductControlMode.OVERRIDE_ENABLED,
            shop_profile=None,
            product_profile=profile,
        ),
    )
    result = ProductDrrPolicyAdapter.from_effective_control(effective)
    assert isinstance(result, ProductDrrPolicyAdapterSuccess)
    assert result.params.profile.target_drr_percent == Decimal(12)
    assert result.provenance.source_scope.value == "PRODUCT"
