"""Перечисления control plane A1 (authoritative, fail-closed)."""

from __future__ import annotations

from enum import Enum


class TriStateCapability(str, Enum):
    """Tri-state capability: UNKNOWN никогда не write-eligible."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"


class AuthoritativeUnknown(str, Enum):
    """Маркер отсутствующего/неизвестного authoritative WB значения."""

    UNKNOWN = "UNKNOWN"


class PaymentTypeAuthority(str, Enum):
    """Нормализованный payment_type из WB (без client defaults)."""

    CPM = "cpm"
    CPC = "cpc"
    UNKNOWN = "UNKNOWN"


class PlacementFlagAuthority(str, Enum):
    """Tri-state флаг размещения: explicit true/false или UNKNOWN."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "UNKNOWN"


class CampaignLegRole(str, Enum):
    """Роль ноги в combined resource (не legacy type 8/9)."""

    AUTO = "auto"
    SEARCH = "search"


class CampaignTopology(str, Enum):
    """Топология combined campaign resource по authoritative WB legs."""

    AUTO_ONLY = "auto_only"
    SEARCH_ONLY = "search_only"
    AUTO_AND_SEARCH = "auto_and_search"
    UNKNOWN = "UNKNOWN"


class BidTypeAuthority(str, Enum):
    """Нормализованный bid_type из WB v2."""

    UNIFIED = "unified"
    MANUAL = "manual"
    UNKNOWN = "UNKNOWN"


class WbCampaignStatusAuthority(str, Enum):
    """Статус WB v2 adverts; UNKNOWN при отсутствии/неизвестном значении."""

    DELETED = "-1"
    READY = "4"
    DONE = "7"
    CANCELLED = "8"
    ACTIVE = "9"
    PAUSE = "11"
    UNKNOWN = "UNKNOWN"


class CanonicalOperationKind(str, Enum):
    """Bounded existing-resource operation subset A1."""

    SET_BUDGET_POLICY = "campaign.set_budget_policy"
    SET_SALES_POLICY = "campaign.set_sales_policy"
    SET_BID_CONTROL_POLICY = "campaign.set_bid_control_policy"


class ProductMembershipAuthority(str, Enum):
    """Authoritative product membership certainty from nm_settings."""

    KNOWN = "known"
    KNOWN_EMPTY = "known_empty"
    UNKNOWN = "UNKNOWN"


class MappingStatus(str, Enum):
    """Статус сопоставления registry anchor ↔ authoritative WB read."""

    OK = "ok"
    BROKEN = "broken"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


class DryRunStatus(str, Enum):
    """Итог dry-run pipeline."""

    OK = "ok"
    REJECTED = "rejected"
    NO_OP = "no_op"
