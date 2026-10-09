"""Read-only проекция campaign↔product bindings (Slice B)."""

from app.modules.product_control.application.projection.campaign_binding_projector import (
    CampaignProductBindingProjector,
)
from app.modules.product_control.application.projection.sources import (
    AdvLegProjectionSource,
    ComplexAdvProjectionSource,
    project_complex_adv,
)

__all__ = [
    "AdvLegProjectionSource",
    "CampaignProductBindingProjector",
    "ComplexAdvProjectionSource",
    "project_complex_adv",
]
