"""Валидатор и генератор machine-readable registry для scripts lane.

Модуль владеет только Registry v2: строгой проверкой YAML-документа,
детерминированным представлением `scripts/REGISTRY.md` и drift-check.
Resolver загружает тот же документ из зафиксированного Git HEAD.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

SCHEMA_NAME = "scripts-registry"
SCHEMA_VERSION = 2
MARKDOWN_PATH = "scripts/REGISTRY.md"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PATH_PATTERN = re.compile(r"^[^/].*[^/]$")
IMMUTABLE_IMAGE_PATTERN = re.compile(
    r"^harbor\.skyline360\.ru/git-registry-cache/"
    r"revoluxe-ai/adv-bot:[0-9a-f]{40}$"
)
ARG_TYPES = {"string", "integer", "number", "boolean", "date", "path", "enum"}
TENANT_SCOPES = {"GENERIC", "PARAMETERIZED", "SPECIAL_PURPOSE"}
SIDE_EFFECTS = {"READ_ONLY", "LOCAL_ARTIFACT_WRITE", "EXTERNAL_READ"}
READINESS_KEYS = {
    "runnable",
    "tests",
    "battle_tested",
    "last_local_at",
    "last_cluster_at",
    "last_image_ref",
    "notes",
}
BASE_KEYS = {
    "id",
    "title",
    "path",
    "resolution_enabled",
    "explicit_invocation_enabled",
    "deprecated_by",
    "readiness",
}
AUTOMATIC_KEYS = {
    "capabilities",
    "sources",
    "provided_fields",
    "required_args",
    "optional_args",
    "output_schema_version",
    "primary_artifact_pattern",
    "tenant_scope",
    "hardcoded_context",
    "composable",
    "compose_with",
    "side_effects",
}
INVOCATION_KEYS = {
    "provided_fields",
    "required_args",
    "optional_args",
    "output_schema_version",
    "primary_artifact_pattern",
    "tenant_scope",
    "hardcoded_context",
    "side_effects",
}
ENABLED_REQUIRED_KEYS = BASE_KEYS | AUTOMATIC_KEYS
EXPLICIT_REQUIRED_KEYS = BASE_KEYS | INVOCATION_KEYS
LEDGER_KEYS = BASE_KEYS
HARDCODED_IDENTITY = re.compile(
    r"\b(?:SHOP_ID|WB_CABINET_ID|PROJECT_ID|BRANCH_NAME|REPORT_ID)\s*="
)


class RegistryValidationError(ValueError):
    """Ошибка строгой валидации Registry v2 с машиночитаемым списком причин."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def _is_mapping(value: Any) -> bool:
    """Проверить mapping без принятия произвольных sequence-объектов."""
    return isinstance(value, Mapping)


def _validate_mapping_order(
    value: Any, field: str, errors: list[str]
) -> None:
    """Проверить lexicographic order всех YAML mapping keys."""
    if isinstance(value, Mapping):
        keys = list(value)
        if all(isinstance(key, str) for key in keys) and keys != sorted(keys):
            errors.append(f"{field}: mapping keys must be lexicographically sorted")
        for key, child in value.items():
            _validate_mapping_order(child, f"{field}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_mapping_order(child, f"{field}[{index}]", errors)


def _require_string(value: Any, field: str, errors: list[str]) -> None:
    """Добавить ошибку, если поле не является непустой строкой."""
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field}: expected non-empty string")


def _validate_string_list(value: Any, field: str, errors: list[str]) -> None:
    """Проверить уникальный непустой список строк."""
    if not isinstance(value, list):
        errors.append(f"{field}: expected list")
        return
    if any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{field}: every item must be a non-empty string")
    if len(value) != len(set(value)):
        errors.append(f"{field}: duplicate values")


def _validate_argument_map(value: Any, field: str, errors: list[str]) -> None:
    """Проверить exact shape аргументных спецификаций Registry."""
    if not _is_mapping(value):
        errors.append(f"{field}: expected mapping")
        return
    for name, specification in value.items():
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{field}: argument name must be non-empty string")
            continue
        if not _is_mapping(specification):
            errors.append(f"{field}.{name}: expected mapping")
            continue
        if set(specification) != {"type", "description", "secret"}:
            errors.append(
                f"{field}.{name}: keys must be type, description, secret"
            )
        if specification.get("type") not in ARG_TYPES:
            errors.append(f"{field}.{name}.type: invalid argument type")
        if not isinstance(specification.get("description"), str):
            errors.append(f"{field}.{name}.description: expected string")
        if not isinstance(specification.get("secret"), bool):
            errors.append(f"{field}.{name}.secret: expected boolean")


def _validate_readiness(value: Any, field: str, errors: list[str]) -> None:
    """Проверить readiness metadata без изменения пользовательских notes."""
    if not _is_mapping(value):
        errors.append(f"{field}: expected mapping")
        return
    if set(value) != READINESS_KEYS:
        errors.append(f"{field}: keys must be {sorted(READINESS_KEYS)}")
    if value.get("runnable") not in {"UNKNOWN", "WORKS", "BROKEN"}:
        errors.append(f"{field}.runnable: invalid value")
    if value.get("tests") not in {"NONE", "PARTIAL", "COVERED"}:
        errors.append(f"{field}.tests: invalid value")
    if value.get("battle_tested") not in {"NO", "YES"}:
        errors.append(f"{field}.battle_tested: invalid value")
    for key in ("last_local_at", "last_cluster_at", "last_image_ref", "notes"):
        if not isinstance(value.get(key), str):
            errors.append(f"{field}.{key}: expected string")
    image_ref = value.get("last_image_ref")
    if isinstance(image_ref, str) and image_ref != "-" and not IMMUTABLE_IMAGE_PATTERN.fullmatch(
        image_ref
    ):
        errors.append(f"{field}.last_image_ref: expected immutable Harbor image or '-'")


def _validate_common_entry(
    entry: Mapping[str, Any], index: int, errors: list[str]
) -> None:
    """Проверить identity/flags, общие для всех Registry rows."""
    prefix = f"entries[{index}]"
    if set(entry) < BASE_KEYS:
        missing = sorted(BASE_KEYS - set(entry))
        errors.append(f"{prefix}: missing keys {missing}")
    if not isinstance(entry.get("id"), str) or not ID_PATTERN.fullmatch(
        str(entry.get("id", ""))
    ):
        errors.append(f"{prefix}.id: expected kebab-case")
    for key in ("title", "path"):
        _require_string(entry.get(key), f"{prefix}.{key}", errors)
    path = entry.get("path")
    if isinstance(path, str) and (
        "\\" in path
        or path.startswith("/")
        or ".." in Path(path).parts
        or not PATH_PATTERN.fullmatch(path)
    ):
        errors.append(f"{prefix}.path: expected repository-relative POSIX path")
    for key in ("resolution_enabled", "explicit_invocation_enabled"):
        if not isinstance(entry.get(key), bool):
            errors.append(f"{prefix}.{key}: expected boolean")
    deprecated_by = entry.get("deprecated_by")
    if deprecated_by is not None and not isinstance(deprecated_by, str):
        errors.append(f"{prefix}.deprecated_by: expected string or null")
    _validate_readiness(entry.get("readiness"), f"{prefix}.readiness", errors)


def _validate_contract_fields(
    entry: Mapping[str, Any], index: int, errors: list[str], *, automatic: bool
) -> None:
    """Проверить automatic либо explicit invocation metadata."""
    prefix = f"entries[{index}]"
    required = AUTOMATIC_KEYS if automatic else INVOCATION_KEYS
    missing = sorted(required - set(entry))
    if missing:
        errors.append(f"{prefix}: missing contract keys {missing}")
    for field in ("capabilities", "sources", "provided_fields"):
        if field in required:
            _validate_string_list(entry.get(field), f"{prefix}.{field}", errors)
    _validate_argument_map(entry.get("required_args"), f"{prefix}.required_args", errors)
    _validate_argument_map(entry.get("optional_args"), f"{prefix}.optional_args", errors)
    if (
        isinstance(entry.get("required_args"), Mapping)
        and isinstance(entry.get("optional_args"), Mapping)
        and set(entry["required_args"]) & set(entry["optional_args"])
    ):
        errors.append(f"{prefix}: required_args and optional_args overlap")
    for field in ("output_schema_version", "primary_artifact_pattern"):
        _require_string(entry.get(field), f"{prefix}.{field}", errors)
    if entry.get("tenant_scope") not in TENANT_SCOPES:
        errors.append(f"{prefix}.tenant_scope: invalid value")
    hardcoded = entry.get("hardcoded_context")
    if not _is_mapping(hardcoded) or set(hardcoded) != {
        "identifiers",
        "justification",
    }:
        errors.append(f"{prefix}.hardcoded_context: invalid shape")
    elif not isinstance(hardcoded.get("identifiers"), list) or not isinstance(
        hardcoded.get("justification"), str
    ):
        errors.append(f"{prefix}.hardcoded_context: invalid field types")
    if automatic:
        if not isinstance(entry.get("composable"), bool):
            errors.append(f"{prefix}.composable: expected boolean")
        if not isinstance(entry.get("compose_with"), list):
            errors.append(f"{prefix}.compose_with: expected list")
        if not isinstance(entry.get("side_effects"), list):
            errors.append(f"{prefix}.side_effects: expected list")
        else:
            if any(item not in SIDE_EFFECTS for item in entry["side_effects"]):
                errors.append(f"{prefix}.side_effects: invalid value")
            if "READ_ONLY" not in entry["side_effects"]:
                errors.append(f"{prefix}.side_effects: READ_ONLY is required")
    else:
        side_effects = entry.get("side_effects")
        if not isinstance(side_effects, list) or any(
            item not in SIDE_EFFECTS for item in side_effects
        ):
            errors.append(f"{prefix}.side_effects: invalid value")
        elif "READ_ONLY" not in side_effects:
            errors.append(f"{prefix}.side_effects: READ_ONLY is required")


def validate_document(document: Any) -> dict[str, Any]:
    """Проверить и вернуть Registry v2 document.

    Args:
        document: YAML-документ, уже разобранный в Python object.

    Returns:
        Тот же документ при успешной проверке.

    Raises:
        RegistryValidationError: если нарушена структура или conditional schema.
    """
    errors: list[str] = []
    if not _is_mapping(document):
        raise RegistryValidationError(["document: expected mapping"])
    _validate_mapping_order(document, "document", errors)
    if set(document) != {"schema", "version", "generated", "entries"}:
        errors.append("document: top-level keys must be schema, version, generated, entries")
    if document.get("schema") != SCHEMA_NAME:
        errors.append(f"schema: expected {SCHEMA_NAME}")
    if document.get("version") != SCHEMA_VERSION:
        errors.append(f"version: expected integer {SCHEMA_VERSION}")
    generated = document.get("generated")
    if not _is_mapping(generated) or set(generated) != {"markdown", "ordering"}:
        errors.append("generated: keys must be markdown and ordering")
    else:
        if generated.get("markdown") != MARKDOWN_PATH:
            errors.append(f"generated.markdown: expected {MARKDOWN_PATH}")
        if generated.get("ordering") != "id":
            errors.append("generated.ordering: expected id")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("entries: expected non-empty list")
        entries = []
    entry_ids = [
        entry.get("id")
        for entry in entries
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    ]
    if entry_ids != sorted(entry_ids):
        errors.append("entries: must be sorted by id")
    ids: set[str] = set()
    paths: set[str] = set()
    for index, raw_entry in enumerate(entries):
        if not _is_mapping(raw_entry):
            errors.append(f"entries[{index}]: expected mapping")
            continue
        entry = raw_entry
        _validate_common_entry(entry, index, errors)
        entry_id = entry.get("id")
        path = entry.get("path")
        if isinstance(entry_id, str):
            if entry_id in ids:
                errors.append(f"entries[{index}].id: duplicate {entry_id}")
            ids.add(entry_id)
        if isinstance(path, str):
            if path in paths:
                errors.append(f"entries[{index}].path: duplicate {path}")
            paths.add(path)
        resolution_enabled = entry.get("resolution_enabled") is True
        explicit_enabled = entry.get("explicit_invocation_enabled") is True
        allowed = (
            ENABLED_REQUIRED_KEYS
            if resolution_enabled
            else EXPLICIT_REQUIRED_KEYS
            if explicit_enabled
            else LEDGER_KEYS
        )
        unknown = sorted(set(entry) - allowed)
        if unknown:
            errors.append(f"entries[{index}]: unknown keys {unknown}")
        if resolution_enabled:
            _validate_contract_fields(entry, index, errors, automatic=True)
            compose_with = entry.get("compose_with")
            if isinstance(compose_with, list):
                if any(not isinstance(item, str) for item in compose_with):
                    errors.append(
                        f"entries[{index}].compose_with: dependencies must be strings"
                    )
                if entry.get("composable") is False and compose_with:
                    errors.append(f"entries[{index}].compose_with: must be empty")
                if entry.get("composable") is True and not compose_with:
                    errors.append(
                        f"entries[{index}].compose_with: composable rows need predecessors"
                    )
                if all(isinstance(item, str) for item in compose_with) and len(
                    compose_with
                ) != len(set(compose_with)):
                    errors.append(f"entries[{index}].compose_with: duplicate dependency")
                if isinstance(entry.get("id"), str) and entry.get("id") in compose_with:
                    errors.append(f"entries[{index}].compose_with: self-reference")
        elif explicit_enabled:
            _validate_contract_fields(entry, index, errors, automatic=False)
    for index, raw_entry in enumerate(entries):
        if not _is_mapping(raw_entry):
            continue
        deprecated_by = raw_entry.get("deprecated_by")
        if isinstance(deprecated_by, str) and deprecated_by not in ids:
            errors.append(f"entries[{index}].deprecated_by: unknown id {deprecated_by}")
        compose_with = raw_entry.get("compose_with")
        if isinstance(compose_with, list):
            for item in compose_with:
                if item not in ids:
                    errors.append(f"entries[{index}].compose_with: unknown id {item}")
                elif not any(
                    isinstance(candidate, Mapping)
                    and candidate.get("id") == item
                    and candidate.get("resolution_enabled") is True
                    and candidate.get("composable") is True
                    for candidate in entries
                ):
                    errors.append(
                        f"entries[{index}].compose_with: dependency {item} is not composable"
                    )
    graph: dict[str, set[str]] = {}
    for entry in entries:
        if (
            not isinstance(entry, Mapping)
            or entry.get("resolution_enabled") is not True
            or entry.get("composable") is not True
        ):
            continue
        dependencies = entry.get("compose_with", [])
        graph[str(entry["id"])] = (
            set(dependencies)
            if isinstance(dependencies, list)
            and all(isinstance(item, str) for item in dependencies)
            else set()
        )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        """Проверить отсутствие cycle в Registry composition graph."""
        if node in visiting:
            errors.append(f"entries.compose_with: cycle detected at {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, set()):
            if dependency in graph:
                visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    if errors:
        raise RegistryValidationError(errors)
    return dict(document)


def load_registry(path: Path) -> dict[str, Any]:
    """Загрузить и строго провалидировать YAML registry с диска."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryValidationError([f"{path}: cannot load YAML: {exc}"]) from exc
    return validate_document(document)


def load_registry_text(text: str) -> dict[str, Any]:
    """Загрузить и строго провалидировать registry text из Git blob."""
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RegistryValidationError([f"registry text: invalid YAML: {exc}"]) from exc
    return validate_document(document)


def _cell(value: Any) -> str:
    """Экранировать значение для markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(document: Mapping[str, Any]) -> str:
    """Детерминированно отрендерить human-readable registry projection."""
    normalized = validate_document(dict(document))
    entries = normalized["entries"]
    lines = [
        "# scripts/ readiness registry",
        "",
        "Ledger for `/opsx-scripts` (daily) and `/opsx-scripts-prepare`.",
        "",
        "Human display: `Title (path)` — see `.cursor/commands/opsx-human-label-display.md`.",
        "",
        "Do not set `battle_tested=YES` without Owner `RECORD_BATTLE GO` + evidence.",
        "",
        "## Schema",
        "",
        "| title | path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |",
        "|-------|------|----------|-------|---------------|----------------|-----------------|----------------|-------|",
        "| short human name | `scripts/<entrypoint>` | `UNKNOWN` \\| `WORKS` \\| `BROKEN` | `NONE` \\| `PARTIAL` \\| `COVERED` | `NO` \\| `YES` | ISO UTC or `-` | ISO UTC or `-` | image ref or `-` | short |",
        "",
        "## Entrypoints",
        "",
        "| title | path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |",
        "|-------|------|----------|-------|---------------|----------------|-----------------|----------------|-------|",
    ]
    for entry in entries:
        readiness = entry["readiness"]
        lines.append(
            "| "
            + " | ".join(
                _cell(
                    entry[field]
                    if field in {"title", "path"}
                    else readiness.get(field)
                )
                for field in (
                    "title",
                    "path",
                    "runnable",
                    "tests",
                    "battle_tested",
                    "last_local_at",
                    "last_cluster_at",
                    "last_image_ref",
                    "notes",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Support (not Job entrypoints)",
            "",
            "Tracked only as notes; not run via `ops-script-runner` unless Owner promotes:",
            "",
            "* `scripts/set_path.py` — path bootstrap",
            "* `scripts/template_script.py` — authoring template",
            "* `scripts/__init__.py` and package `__init__.py` / helper modules under `send_message/utils`, `get_users/filters`, etc.",
            "",
            "## Infra pointers",
            "",
            "* Prepare: `/opsx-scripts-prepare`",
            "* Operate: `/opsx-scripts`",
            "* Display SoT: `.cursor/commands/opsx-human-label-display.md`",
            "* Workflow: `.github/workflows/deploy_scripts.yml` (branch `scripts`, tag `scripts`; CI push GHCR only)",
            "* Cluster Job image (Harbor proxy-cache pull-through): `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:<commit-sha>`",
            "* Job template: `k8s/jobs/ops-script-runner.yaml` (`__HOLD_SECONDS__` default 900)",
            "* Artifact cp helper: `scripts/ops_script_job_cp.ps1` (retry kubectl cp + sha256 gate)",
            "",
        ]
    )
    return "\n".join(lines)


def hardcoding_errors(entry: Mapping[str, Any], source_text: str) -> list[str]:
    """Найти undeclared fixed identity только для resolution-enabled row.

    Legacy и explicit-only rows намеренно пропускаются: их hardcoding не
    блокирует R1 automatic resolution, но explicit selection остаётся safety
    gated отдельным contract validator.
    """
    if entry.get("resolution_enabled") is not True:
        return []
    if entry.get("tenant_scope") == "SPECIAL_PURPOSE":
        return []
    declared = {
        token.rsplit(":", 1)[-1]
        for token in entry.get("hardcoded_context", {}).get("identifiers", [])
        if isinstance(token, str) and ":" in token
    }
    errors: list[str] = []
    for line_number, line in enumerate(source_text.splitlines(), start=1):
        match = HARDCODED_IDENTITY.search(line)
        fixed_literal = match and re.search(
            r"=\s*(?P<literal>\"[^\"]*\"|'[^']*'|[1-9][0-9]*)\s*(?:#.*)?$",
            line,
        )
        literal = fixed_literal.group("literal") if fixed_literal else ""
        if (
            literal not in {'""', "''", ""}
            and fixed_literal
            and str(line_number) not in declared
        ):
            errors.append(f"{entry.get('path')}:{line_number}: undeclared fixed identity")
    return errors


def _write_json(value: Mapping[str, Any]) -> None:
    """Вывести единичный machine-readable maintenance result."""
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    """Выполнить validate/render/check-drift с фиксированными exit codes."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True, type=Path)
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--input", required=True, type=Path)
    render_parser.add_argument("--output", required=True, type=Path)
    drift_parser = subparsers.add_parser("check-drift")
    drift_parser.add_argument("--input", required=True, type=Path)
    drift_parser.add_argument("--generated", required=True, type=Path)
    gate_parser = subparsers.add_parser("hardcoding-gate")
    gate_parser.add_argument("--input", required=True, type=Path)
    gate_parser.add_argument("--root", required=True, type=Path)
    gate_parser.add_argument("--changed", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        document = load_registry(args.input)
        rendered = render_markdown(document)
        if args.command == "validate":
            _write_json({"status": "VALID", "path": str(args.input)})
            return 0
        if args.command == "render":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            _write_json({"status": "RENDERED", "path": str(args.output)})
            return 0
        if args.command == "hardcoding-gate":
            changed = set(args.changed)
            errors: list[str] = []
            for entry in document["entries"]:
                if changed and entry["path"] not in changed:
                    continue
                source_path = args.root / entry["path"]
                if not source_path.is_file():
                    errors.append(f"{entry['path']}: source file is missing")
                    continue
                errors.extend(
                    hardcoding_errors(
                        entry, source_path.read_text(encoding="utf-8")
                    )
                )
            _write_json(
                {"status": "PASS" if not errors else "FAIL", "errors": errors}
            )
            return 0 if not errors else 2
        expected = args.generated.read_text(encoding="utf-8")
        if expected != rendered:
            _write_json({"status": "DRIFT", "path": str(args.generated)})
            return 3
        _write_json({"status": "IN_SYNC", "path": str(args.generated)})
        return 0
    except RegistryValidationError as exc:
        _write_json({"status": "INVALID", "errors": list(exc.errors)})
        return 2
    except (OSError, ValueError) as exc:
        _write_json({"status": "ERROR", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
