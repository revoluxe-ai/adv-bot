"""Сборка ResolverContext для экрана настроек. Enrollment не выдумывается."""

from __future__ import annotations

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    ControlPathKind,
    HierarchicalEnrollment,
)
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolverContext,
    ShopFeatureSlot,
)

# Slice B не хранит enrollment. Пока порт не появится, экран fail-closed.
UI_ENROLLMENT = HierarchicalEnrollment.NOT_ENROLLED
# Путь контроллера тоже не колонка Slice B. LEGACY не утверждаем.
# NOT_ENROLLED останавливает resolver раньше effective policy.
UI_CONTROL_PATH = ControlPathKind.HIERARCHICAL


def build_settings_context(
    *,
    shop_id: str,
    advert_id: int,
    shop_features: dict[AdControlFeatureId, ShopFeatureSlot],
    campaign_features: dict[AdControlFeatureId, CampaignFeatureSlot],
) -> ResolverContext:
    """Контекст экрана. product_drr не загружается в 4.2A."""
    return ResolverContext(
        enrollment=UI_ENROLLMENT,
        control_path=UI_CONTROL_PATH,
        shop_id=shop_id,
        shop_features=shop_features,
        campaign=CampaignRef(shop_id=shop_id, advert_id=advert_id),
        campaign_features=campaign_features,
        product_drr=None,
    )
