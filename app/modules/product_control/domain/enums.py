"""Перечисления enrollment, режимов продукта и ролей привязок."""

from __future__ import annotations

from enum import StrEnum


class ShopControlEnrollment(StrEnum):
    """Мастер-гейт rollout product control на уровне магазина."""

    NOT_ENROLLED = "NOT_ENROLLED"
    ENROLLED = "ENROLLED"
    BLOCKED = "BLOCKED"


class ProductControlMode(StrEnum):
    """Поведение product control для ``(shop_id, nmid)`` при открытом shop gate."""

    INHERIT_SHOP = "INHERIT_SHOP"
    OVERRIDE_ENABLED = "OVERRIDE_ENABLED"
    BLOCKED = "BLOCKED"


class LegRole(StrEnum):
    """Физическая нога кампании (Auto и Search — раздельные adv_id)."""

    AUTO = "AUTO"
    SEARCH = "SEARCH"


class MembershipRole(StrEnum):
    """
    Роль nmID в membership комплекса.

    PRIMARY допускается только при явном evidence; иначе UNKNOWN.
    """

    PRIMARY = "PRIMARY"
    UNKNOWN = "UNKNOWN"


class DrrResolutionTier(StrEnum):
    """Уровень, с которого взят атомарный DrrProfile (без field-level mix)."""

    PRODUCT = "PRODUCT"
    CATEGORY = "CATEGORY"  # зарезервировано; runtime не реализован в Slice A
    SHOP = "SHOP"
    LEGACY = "LEGACY"


class EffectiveControlOutcomeKind(StrEnum):
    """Итог effective control до адаптера кампании."""

    LEGACY_NOT_ENROLLED = "LEGACY_NOT_ENROLLED"
    LEGACY_TIER = "LEGACY_TIER"
    ACTIVE_DRR_PROFILE = "ACTIVE_DRR_PROFILE"
    PRODUCT_CONTROL_BLOCKED = "PRODUCT_CONTROL_BLOCKED"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"


class ProductControlBlockerReason(StrEnum):
    """Коды блокировки / fail-closed для product control plane."""

    BLOCKED_BY_PRODUCT_PRICE_SOURCE = "BLOCKED_BY_PRODUCT_PRICE_SOURCE"
    PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS = "PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    SHOP_CONTROL_BLOCKED = "SHOP_CONTROL_BLOCKED"
    PRODUCT_CONTROL_BLOCKED = "PRODUCT_CONTROL_BLOCKED"
