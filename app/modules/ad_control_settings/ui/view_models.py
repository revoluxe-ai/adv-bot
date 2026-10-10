"""
Проекции configured/effective для экрана Advertising Control.

Effective берётся только из ``AdControlSettingsResolver``.
При ``NOT_ENROLLED`` resolver fail-closed: UI показывает код, не подмену.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ad_control_settings.domain.configured_state import (
    project_configured_campaign_features,
    project_configured_shop_features,
)
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.registry import FEATURE_REGISTRY
from app.modules.ad_control_settings.domain.resolver import AdControlSettingsResolver
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolvedFeaturePolicy,
    ResolverBlocked,
    ResolverContext,
    ShopFeatureSlot,
)
from app.modules.ad_control_settings.ui.labels import feature_label, summarize_payload


@dataclass(frozen=True, slots=True)
class ShopFeatureLine:
    """Одна shop-feature без campaign identity."""

    feature_id: AdControlFeatureId
    label: str
    activation: ShopFeatureActivation
    payload_text: str


@dataclass(frozen=True, slots=True)
class FeatureControlLine:
    """Одна feature на кампании: configured, effective, provenance, блок."""

    feature_id: AdControlFeatureId
    label: str
    shop_activation: str
    shop_payload_text: str
    campaign_mode: AdControlFeatureMode
    campaign_payload_text: str
    effective_text: str
    provenance_text: str
    status_text: str
    blocked: bool


def summarize_campaign_modes(
    campaign_features: dict[AdControlFeatureId, CampaignFeatureSlot],
) -> str:
    """Короткая строка режимов. Нет строки = INHERIT."""
    parts: list[str] = []
    for feature_id in FEATURE_REGISTRY:
        slot = campaign_features.get(
            feature_id,
            CampaignFeatureSlot(mode=AdControlFeatureMode.INHERIT, payload=None),
        )
        parts.append(f"{feature_id.value}={slot.mode.value}")
    return " ".join(parts)


def describe_shop_features(
    shop_features: dict[AdControlFeatureId, ShopFeatureSlot],
) -> tuple[ShopFeatureLine, ...]:
    """
    Shop configured slots.

    Отсутствующий slot = ``DISABLED`` без payload, как в
    ``project_configured_shop_features``.
    """
    lines: list[ShopFeatureLine] = []
    for feature_id in FEATURE_REGISTRY:
        slot = shop_features.get(
            feature_id,
            ShopFeatureSlot(activation=ShopFeatureActivation.DISABLED, payload=None),
        )
        lines.append(
            ShopFeatureLine(
                feature_id=feature_id,
                label=feature_label(feature_id),
                activation=slot.activation,
                payload_text=summarize_payload(slot.payload),
            )
        )
    return tuple(lines)


def describe_campaign_features(
    context: ResolverContext,
) -> tuple[FeatureControlLine, ...]:
    """Собрать строки кампании через проекцию и resolver. Без экономики."""
    shop_by_id = {
        row.feature_id: row for row in project_configured_shop_features(context)
    }
    campaign_by_id = {
        row.feature_id: row for row in project_configured_campaign_features(context)
    }
    lines: list[FeatureControlLine] = []
    for feature_id in FEATURE_REGISTRY:
        shop_row = shop_by_id[feature_id]
        campaign_row = campaign_by_id[feature_id]
        resolved = AdControlSettingsResolver.resolve_feature(context, feature_id)
        lines.append(
            _line(
                feature_id=feature_id,
                shop_activation=shop_row.activation.value,
                shop_payload_text=summarize_payload(shop_row.payload),
                campaign_mode=campaign_row.mode,
                campaign_payload_text=summarize_payload(campaign_row.override_payload),
                resolved=resolved,
            )
        )
    return tuple(lines)


def _line(
    *,
    feature_id: AdControlFeatureId,
    shop_activation: str,
    shop_payload_text: str,
    campaign_mode: AdControlFeatureMode,
    campaign_payload_text: str,
    resolved: ResolvedFeaturePolicy | ResolverBlocked,
) -> FeatureControlLine:
    if isinstance(resolved, ResolverBlocked):
        reasons = ", ".join(code.value for code in resolved.reason_codes)
        blockers = ", ".join(resolved.blockers) if resolved.blockers else "—"
        return FeatureControlLine(
            feature_id=feature_id,
            label=feature_label(feature_id),
            shop_activation=shop_activation,
            shop_payload_text=shop_payload_text,
            campaign_mode=campaign_mode,
            campaign_payload_text=campaign_payload_text,
            effective_text="—",
            provenance_text="—",
            status_text=f"BLOCKED {reasons}; {blockers}",
            blocked=True,
        )
    effective = (
        "inactive" if not resolved.active else summarize_payload(resolved.payload)
    )
    provenance = (
        f"{resolved.provenance.source_kind.value}"
        f"/{resolved.provenance.source_scope.value}"
    )
    reasons = ", ".join(code.value for code in resolved.reason_codes)
    return FeatureControlLine(
        feature_id=feature_id,
        label=feature_label(feature_id),
        shop_activation=shop_activation,
        shop_payload_text=shop_payload_text,
        campaign_mode=campaign_mode,
        campaign_payload_text=campaign_payload_text,
        effective_text=effective,
        provenance_text=provenance,
        status_text=reasons,
        blocked=False,
    )
