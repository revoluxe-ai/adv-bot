"""Перечисления registry, scope и режимов иерархического контроля."""

from __future__ import annotations

from enum import StrEnum


class AdControlScope(StrEnum):
    """Уровни конфигурации иерархического контроля."""

    SHOP = "SHOP"
    PRODUCT = "PRODUCT"
    CAMPAIGN = "CAMPAIGN"
    SYSTEM_LEGACY = "SYSTEM_LEGACY"


class AdControlFeatureId(StrEnum):
    """V1 control features (versioned registry ids)."""

    DRR_POLICY = "DRR_POLICY"
    DYNAMIC_DRR_CONTROL = "DYNAMIC_DRR_CONTROL"
    CPO_INCREASE_ON_HEADROOM = "CPO_INCREASE_ON_HEADROOM"
    CPO_DECREASE_ON_OVERSPEND = "CPO_DECREASE_ON_OVERSPEND"
    CPO_SAFETY_BOUNDS = "CPO_SAFETY_BOUNDS"


class AdControlFeatureMode(StrEnum):
    """Режим feature на campaign (и product при поддержке)."""

    INHERIT = "INHERIT"
    OVERRIDE = "OVERRIDE"
    DISABLED = "DISABLED"


class ShopFeatureActivation(StrEnum):
    """Включение feature на уровне магазина (нет INHERIT на shop)."""

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class ControlPathKind(StrEnum):
    """
    Путь исполнения контроля.

    LEGACY_PASSTHROUGH — явный legacy, не маскируется под hierarchical inherit.
    """

    HIERARCHICAL = "HIERARCHICAL"
    LEGACY_PASSTHROUGH = "LEGACY_PASSTHROUGH"


class HierarchicalEnrollment(StrEnum):
    """Мастер-гейт нового иерархического контроллера."""

    NOT_ENROLLED = "NOT_ENROLLED"
    ENROLLED = "ENROLLED"


class DataSufficiency(StrEnum):
    """Достаточность наблюдаемых метрик для control action."""

    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    STALE = "STALE"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class EffectiveSourceKind(StrEnum):
    """Источник effective configured policy (provenance)."""

    CAMPAIGN_OVERRIDE = "CAMPAIGN_OVERRIDE"
    CAMPAIGN_DISABLED = "CAMPAIGN_DISABLED"
    PRODUCT_OVERRIDE = "PRODUCT_OVERRIDE"
    PRODUCT_DISABLED = "PRODUCT_DISABLED"
    SHOP_POLICY = "SHOP_POLICY"
    SHOP_DISABLED = "SHOP_DISABLED"
    SYSTEM_LEGACY_DEFAULT = "SYSTEM_LEGACY_DEFAULT"
    LEGACY_PASSTHROUGH = "LEGACY_PASSTHROUGH"
    NOT_APPLICABLE = "NOT_APPLICABLE"
