"""Канонический контракт настроек рекламной кампании WB Sky.

Spec: campaign-settings-history.
Модуль хранит transport-independent field/source policy и fail-closed validation.
"""

from .canonical import (
    SCHEMA_VERSION,
    CampaignSettingsSources,
    CanonicalSettingsSnapshot,
    CanonicalizationError,
    build_canonical_settings_snapshot,
    build_canonical_snapshot,
    canonical_state_hash,
    normalize_value,
)
from .inventory import (
    discover_runtime_orm_sources,
    load_runtime_source_fields,
    validate_registry_against_inventory,
)
from .registry import (
    EXCLUDED_SOURCES,
    REGISTERED_SOURCES,
    ContractValidationError,
    ExcelPolicy,
    FieldPolicy,
    HistoryPolicy,
    NormalizationPolicy,
    RegistryContractError,
    SemanticRole,
    SourcePolicy,
    excel_alias,
    excel_editable_fields,
    excel_read_only_fields,
    ordered_shelf_editable_aliases,
    validate_field_inventory,
    validate_registry,
    validate_registry_structure,
    validate_source_inventory,
)

__all__ = [
    "SCHEMA_VERSION",
    "CampaignSettingsSources",
    "CanonicalSettingsSnapshot",
    "CanonicalizationError",
    "build_canonical_settings_snapshot",
    "build_canonical_snapshot",
    "canonical_state_hash",
    "normalize_value",
    "EXCLUDED_SOURCES",
    "REGISTERED_SOURCES",
    "ContractValidationError",
    "RegistryContractError",
    "ExcelPolicy",
    "FieldPolicy",
    "HistoryPolicy",
    "NormalizationPolicy",
    "SemanticRole",
    "SourcePolicy",
    "excel_alias",
    "excel_editable_fields",
    "excel_read_only_fields",
    "ordered_shelf_editable_aliases",
    "validate_field_inventory",
    "validate_registry",
    "validate_registry_structure",
    "validate_source_inventory",
    "discover_runtime_orm_sources",
    "load_runtime_source_fields",
    "validate_registry_against_inventory",
]
