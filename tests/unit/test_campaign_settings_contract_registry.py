"""Contract tests реестра настроек.

Spec: campaign-settings-history.
Проверки фиксируют fail-closed инвариант: новое/удалённое поле или новый ORM source
не могут пройти CI без явной history/Excel policy.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest

from app.modules.campaign_settings_contract import (
    EXCLUDED_SOURCES,
    REGISTERED_SOURCES,
    ContractValidationError,
    ExcelPolicy,
    FieldPolicy,
    HistoryPolicy,
    NormalizationPolicy,
    SemanticRole,
    SourcePolicy,
    validate_field_inventory,
    validate_registry,
    validate_source_inventory,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_MODEL_ROOT = _ROOT / "app/modules/common_slaves/wildberries/models"
_MODEL_FILES = tuple(
    path
    for path in sorted(_MODEL_ROOT.glob("*.py"))
    if path.name != "__init__.py"
)


def _mapped_fields_by_source() -> dict[str, set[str]]:
    """Spec campaign-settings-history: статически извлекает mapped columns без env/DB импорта."""
    out: dict[str, set[str]] = {}
    for path in _MODEL_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            fields: set[str] = set()
            for stmt in node.body:
                name: str | None = None
                value: ast.expr | None = None
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    name, value = stmt.target.id, stmt.value
                elif (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    name, value = stmt.targets[0].id, stmt.value
                if name is None or not isinstance(value, ast.Call):
                    continue
                fn = value.func
                fn_name = (
                    fn.id
                    if isinstance(fn, ast.Name)
                    else fn.attr
                    if isinstance(fn, ast.Attribute)
                    else ""
                )
                if fn_name in {"mapped_column", "Column"}:
                    fields.add(name)
            if fields:
                bases = {ast.unparse(base) for base in node.bases}
                if "BaseTable" in bases:
                    fields.add("id")
                out[node.name] = fields
    return out


def _orm_source_names() -> set[str]:
    """Spec campaign-settings-history: inventory всех ORM source в guarded model roots."""
    return set(_mapped_fields_by_source())


def test_registered_field_inventory_matches_current_orm_exactly() -> None:
    """Spec campaign-settings-history: все 129 current settings fields имеют policy."""
    inventory = _mapped_fields_by_source()
    for source_name in REGISTERED_SOURCES:
        validate_field_inventory(source_name, inventory[source_name])
    assert sum(len(source.fields) for source in REGISTERED_SOURCES.values()) == 129


def test_source_inventory_requires_registered_or_explicit_exclusion() -> None:
    """Spec campaign-settings-history: каждая ORM entity в guarded roots классифицирована."""
    validate_source_inventory(_orm_source_names())


def test_new_field_without_policy_fails_closed() -> None:
    """Spec campaign-settings-history: новая настройка не может быть молча забыта."""
    actual = set(REGISTERED_SOURCES["AdvSetting"].fields)
    actual.add("future_setting_without_policy")

    with pytest.raises(ContractValidationError, match="future_setting_without_policy"):
        validate_field_inventory("AdvSetting", actual)


def test_new_field_with_explicit_policy_passes_paired_positive_case() -> None:
    """Spec campaign-settings-history: после явной policy новый field становится валидным."""
    source = REGISTERED_SOURCES["AdvSetting"]
    fields = dict(source.fields)
    fields["future_setting"] = FieldPolicy(
        name="future_setting",
        semantic_role=SemanticRole.SETTING,
        history=HistoryPolicy.STATE,
        excel=ExcelPolicy.EXCLUDED,
        normalization=NormalizationPolicy.INT,
    )
    custom = dict(REGISTERED_SOURCES)
    custom["AdvSetting"] = replace(
        source,
        fields=MappingProxyType(fields),
    )

    validate_field_inventory("AdvSetting", set(fields), MappingProxyType(custom))


def test_removed_or_renamed_field_rejects_stale_policy() -> None:
    """Spec campaign-settings-history: rename/remove требует синхронного registry update."""
    actual = set(REGISTERED_SOURCES["KeywordSetting"].fields)
    actual.remove("target_place")

    with pytest.raises(ContractValidationError, match="stale_policy=.*target_place"):
        validate_field_inventory("KeywordSetting", actual)


def test_new_orm_source_without_policy_fails_closed() -> None:
    """Spec campaign-settings-history: целиком новый settings source не может проскочить."""
    actual = _orm_source_names() | {"FutureCampaignSettings"}

    with pytest.raises(ContractValidationError, match="FutureCampaignSettings"):
        validate_source_inventory(actual)


def test_new_orm_source_with_explicit_exclusion_passes() -> None:
    """Spec campaign-settings-history: source может быть исключён только с явной причиной."""
    excluded = dict(EXCLUDED_SOURCES)
    excluded["FutureCampaignSettings"] = "explicitly reviewed non-settings runtime entity"

    validate_source_inventory(
        _orm_source_names() | {"FutureCampaignSettings"},
        excluded_sources=MappingProxyType(excluded),
    )


def test_excluded_field_requires_non_empty_reason() -> None:
    """Spec campaign-settings-history: excluded field без reason запрещён fail-closed."""
    source = REGISTERED_SOURCES["KeywordSetting"]
    fields = dict(source.fields)
    fields["auto_block"] = replace(fields["auto_block"], exclusion_reason="")
    custom = dict(REGISTERED_SOURCES)
    custom["KeywordSetting"] = replace(source, fields=MappingProxyType(fields))

    with pytest.raises(ContractValidationError, match="excluded field requires reason"):
        validate_registry(MappingProxyType(custom))


def test_excluded_source_requires_non_empty_reason() -> None:
    """Spec campaign-settings-history: EXCLUDED_SOURCE обязан объяснять исключение."""
    excluded = dict(EXCLUDED_SOURCES)
    excluded["WBCard"] = " "

    with pytest.raises(ContractValidationError, match="excluded source requires"):
        validate_registry(excluded_sources=MappingProxyType(excluded))


def test_every_policy_has_history_excel_and_normalization_dimensions() -> None:
    """Spec campaign-settings-history: ни один field не остаётся с неявным измерением policy."""
    for source in REGISTERED_SOURCES.values():
        for policy in source.fields.values():
            assert isinstance(policy.semantic_role, SemanticRole)
            assert isinstance(policy.history, HistoryPolicy)
            assert isinstance(policy.excel, ExcelPolicy)
            assert isinstance(policy.normalization, NormalizationPolicy)
