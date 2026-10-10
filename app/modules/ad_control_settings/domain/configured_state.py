"""
Проекция configured policy из ResolverContext (без effective resolve).

Не дублирует shop values в campaign INHERIT rows.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ad_control_settings.domain.configured import ConfiguredFeaturePayload
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    AdControlScope,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.registry import FEATURE_REGISTRY
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolverContext,
    ShopFeatureSlot,
)


@dataclass(frozen=True, slots=True)
class ConfiguredShopFeatureState:
    """Configured shop slot (authority at shop scope only)."""

    feature_id: AdControlFeatureId
    scope: AdControlScope
    activation: ShopFeatureActivation
    payload: ConfiguredFeaturePayload | None
    schema_version: int | None


@dataclass(frozen=True, slots=True)
class ConfiguredCampaignFeatureState:
    """
    Configured campaign slot.

    ``override_payload`` задан только при ``mode == OVERRIDE``; INHERIT не копирует shop.
    """

    feature_id: AdControlFeatureId
    scope: AdControlScope
    mode: AdControlFeatureMode
    override_payload: ConfiguredFeaturePayload | None
    schema_version: int | None


def _schema_version(payload: ConfiguredFeaturePayload | None) -> int | None:
    if payload is None:
        return None
    return payload.schema_version


def project_configured_shop_features(
    context: ResolverContext,
) -> tuple[ConfiguredShopFeatureState, ...]:
    """Все V1 features: shop slot из context (или default DISABLED)."""
    rows: list[ConfiguredShopFeatureState] = []
    for feature_id in FEATURE_REGISTRY:
        slot = context.shop_features.get(
            feature_id,
            ShopFeatureSlot(activation=ShopFeatureActivation.DISABLED, payload=None),
        )
        rows.append(
            ConfiguredShopFeatureState(
                feature_id=feature_id,
                scope=AdControlScope.SHOP,
                activation=slot.activation,
                payload=slot.payload,
                schema_version=_schema_version(slot.payload),
            ),
        )
    return tuple(rows)


def project_configured_campaign_features(
    context: ResolverContext,
) -> tuple[ConfiguredCampaignFeatureState, ...]:
    """Все V1 features: campaign mode; payload только для OVERRIDE."""
    rows: list[ConfiguredCampaignFeatureState] = []
    for feature_id in FEATURE_REGISTRY:
        slot = context.campaign_features.get(
            feature_id,
            CampaignFeatureSlot(mode=AdControlFeatureMode.INHERIT, payload=None),
        )
        override_payload = (
            slot.payload if slot.mode == AdControlFeatureMode.OVERRIDE else None
        )
        rows.append(
            ConfiguredCampaignFeatureState(
                feature_id=feature_id,
                scope=AdControlScope.CAMPAIGN,
                mode=slot.mode,
                override_payload=override_payload,
                schema_version=_schema_version(override_payload),
            ),
        )
    return tuple(rows)
