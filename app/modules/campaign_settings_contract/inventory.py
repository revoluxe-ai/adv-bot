"""Source-code inventory validation для spec ``campaign-settings-history``.

Contract gate читает ORM declarations через AST и поэтому не требует env, DI,
PostgreSQL или импорта тяжёлых application settings. Это делает fail-closed
проверку пригодной для CI и preflight.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Set
from pathlib import Path

from app.modules.campaign_settings_contract.registry import (
    EXCLUDED_SOURCES,
    REGISTERED_SOURCES,
    RegistryContractError,
    SourcePolicy,
    validate_registry_structure,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODEL_ROOT = Path("app/modules/common_slaves/wildberries/models")
_CORE_MODELS_FILE = _MODEL_ROOT / "models.py"
_SHELF_MODELS_FILE = _MODEL_ROOT / "auto_shelf_bid_control.py"
_REGISTERED_SOURCE_FILES: Mapping[str, Path] = {
    "AdvSetting": _CORE_MODELS_FILE,
    "KeywordSetting": _CORE_MODELS_FILE,
    "AdvTimeSettings": _CORE_MODELS_FILE,
    "AdvTimeWeekMask": _CORE_MODELS_FILE,
    "AutoShelfBidControlSettings": _SHELF_MODELS_FILE,
}


def _model_files() -> tuple[Path, ...]:
    """Guard every ORM model module in the Wildberries model root, including future files."""
    absolute_root = _REPO_ROOT / _MODEL_ROOT
    return tuple(
        path.relative_to(_REPO_ROOT)
        for path in sorted(absolute_root.glob("*.py"))
        if path.name != "__init__.py"
    )


def _load_tree(relative_path: Path) -> ast.Module:
    """Прочитать Python AST model file для spec campaign-settings-history.

    Helper нужен, чтобы inventory gate анализировал source declarations без
    application imports и без зависимости от runtime env.
    """
    absolute = _REPO_ROOT / relative_path
    try:
        source = absolute.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise RegistryContractError(f"cannot read model source {relative_path}: {exc}") from exc
    try:
        return ast.parse(source, filename=str(relative_path))
    except SyntaxError as exc:
        raise RegistryContractError(f"cannot parse model source {relative_path}: {exc}") from exc


def _call_name(value: ast.expr | None) -> str:
    """Вернуть short call name для AST field declaration.

    Spec campaign-settings-history использует это только для mapped_column/Column
    inventory, чтобы новый declared ORM field нельзя было silently пропустить.
    """
    if not isinstance(value, ast.Call):
        return ""
    func = value.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _declared_mapped_fields(class_node: ast.ClassDef) -> set[str]:
    """Снять mapped fields одного ORM class из AST.

    Для BaseTable descendants добавляется inherited `id`, потому что это реальная
    mapped column и spec campaign-settings-history требует policy даже для неё.
    """
    fields: set[str] = set()
    for statement in class_node.body:
        field_name: str | None = None
        value: ast.expr | None = None
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            field_name = statement.target.id
            value = statement.value
        elif (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            field_name = statement.targets[0].id
            value = statement.value
        if field_name and _call_name(value) in {"mapped_column", "Column"}:
            fields.add(field_name)
    base_names = {
        base.id for base in class_node.bases if isinstance(base, ast.Name)
    }
    if "BaseTable" in base_names:
        fields.add("id")
    return fields


def _has_explicit_tablename(class_node: ast.ClassDef) -> bool:
    """Определить explicit ORM table declaration для source discovery.

    Это дополняет mapped-field detection для classes без локальных columns и
    обеспечивает source-level gate spec campaign-settings-history.
    """
    for statement in class_node.body:
        if not isinstance(statement, ast.Assign):
            continue
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id == "__tablename__":
                return True
    return False


def _class_inventory(relative_path: Path) -> dict[str, frozenset[str]]:
    """Снять ORM-like class inventory одного reviewed model root.

    Функция нужна exact source coverage spec campaign-settings-history и не
    принимает imported classes, потому что AST видит только local declarations.
    """
    inventory: dict[str, frozenset[str]] = {}
    for node in _load_tree(relative_path).body:
        if not isinstance(node, ast.ClassDef):
            continue
        fields = _declared_mapped_fields(node)
        if not fields and not _has_explicit_tablename(node):
            continue
        inventory[node.name] = frozenset(fields)
    return inventory


def load_runtime_source_fields() -> dict[str, frozenset[str]]:
    """Снять exact declared-field inventory registered settings sources.

    Имя API сохранено как runtime-compatible contract, но реализация намеренно
    static/AST: CI должен ловить field drift без запуска application runtime.
    """
    by_file = {path: _class_inventory(path) for path in set(_REGISTERED_SOURCE_FILES.values())}
    out: dict[str, frozenset[str]] = {}
    for source_name, relative_path in _REGISTERED_SOURCE_FILES.items():
        try:
            out[source_name] = by_file[relative_path][source_name]
        except KeyError as exc:
            raise RegistryContractError(
                f"{source_name}: source declaration is missing in {relative_path}"
            ) from exc
    return out


def discover_runtime_orm_sources() -> frozenset[str]:
    """Найти все ORM source candidates в reviewed model roots.

    Spec campaign-settings-history требует exact REGISTERED/EXCLUDED_SOURCE
    classification, поэтому новая local ORM class автоматически создаёт drift.
    """
    names: set[str] = set()
    for relative_path in _model_files():
        names.update(_class_inventory(relative_path))
    return frozenset(names)


def validate_registry_against_inventory(
    *,
    runtime_fields: Mapping[str, Set[str]] | None = None,
    discovered_sources: Set[str] | None = None,
    registered: Mapping[str, SourcePolicy] = REGISTERED_SOURCES,
    excluded_sources: Mapping[str, str] = EXCLUDED_SOURCES,
) -> None:
    """Fail closed при source/field drift canonical registry.

    Это основной CI invariant spec campaign-settings-history: любое новое,
    удалённое или переименованное поле/source требует явного contract update.
    """
    validate_registry_structure(registered, excluded_sources)
    actual_sources = (
        frozenset(discovered_sources)
        if discovered_sources is not None
        else discover_runtime_orm_sources()
    )
    classified_sources = frozenset(registered) | frozenset(excluded_sources)
    if actual_sources != classified_sources:
        unknown = sorted(actual_sources - classified_sources)
        stale = sorted(classified_sources - actual_sources)
        raise RegistryContractError(
            f"ORM source inventory drift: unknown={unknown}, stale={stale}"
        )

    actual_fields = (
        {name: frozenset(fields) for name, fields in runtime_fields.items()}
        if runtime_fields is not None
        else load_runtime_source_fields()
    )
    if set(actual_fields) != set(registered):
        unknown = sorted(set(actual_fields) - set(registered))
        missing = sorted(set(registered) - set(actual_fields))
        raise RegistryContractError(
            f"registered source field inventory drift: unknown={unknown}, missing={missing}"
        )

    for source_name, source in registered.items():
        expected = frozenset(source.fields)
        actual = actual_fields[source_name]
        if actual != expected:
            added = sorted(actual - expected)
            removed = sorted(expected - actual)
            raise RegistryContractError(
                f"{source_name}: field inventory drift added={added}, removed={removed}"
            )


__all__ = [
    "discover_runtime_orm_sources",
    "load_runtime_source_fields",
    "validate_registry_against_inventory",
]
