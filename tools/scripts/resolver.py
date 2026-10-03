"""Детерминированный resolver lifecycle-контракта scripts lane.

Resolver получает JSON request, проверяет caller/canonical Git topology,
читает Registry и execution inputs из immutable canonical HEAD и печатает
ровно один JSON result. Он не создаёт файлы, не запускает Jobs и не выполняет
Git writes; operational outcomes ограничены REUSE, COMPOSE,
FORMAL_CHANGE_REQUIRED и BLOCKED.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[2]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from tools.scripts.registry import (
    RegistryValidationError,
    load_registry_text,
    render_markdown,
)

REQUEST_SCHEMA = "scripts-resolver-request.v1"
RESULT_SCHEMA = "scripts-resolver-result.v1"
FORMAL_SCHEMA = "opsx.formal-change-handoff.v1"
COMPOSE_SCHEMA = "scripts-compose-plan.v1"
HEX_SHA = re.compile(r"^[0-9a-f]{40}$")
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
SECRET_NAME = re.compile(
    r"(?i)(?:token|secret|password|api[_-]?key|authorization|cookie|credential)"
)
BEARER_VALUE = re.compile(r"(?i)^bearer\s+\S+$")
JWT_VALUE = re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
OUTCOMES = {"REUSE", "COMPOSE", "FORMAL_CHANGE_REQUIRED", "BLOCKED"}
VALID_MODES = {"PLAN_RUN", "RUN"}
REQUEST_KEYS = {
    "schema_version",
    "mode",
    "request_id",
    "run_id",
    "change_name_hint",
    "capabilities",
    "sources",
    "required_fields",
    "output_schema_version",
    "primary_artifact_pattern",
    "required_args",
    "optional_args",
    "zero_write_required",
    "explicit_script",
    "owning_change_id",
}


class InvalidRequest(ValueError):
    """Ошибка пользовательского resolver request, не допускающая matching."""


class ResolverBlocked(RuntimeError):
    """Безопасная остановка из-за отсутствующей topology/registry evidence."""


@dataclass(frozen=True)
class GitIdentity:
    """Проверенная identity Git worktree для provenance."""

    root: Path
    branch: str
    sha: str
    common_dir: Path

    def as_result(self) -> dict[str, str]:
        """Вернуть JSON-совместимую provenance identity."""
        return {
            "root": str(self.root),
            "branch": self.branch,
            "sha": self.sha,
            "common_dir": str(self.common_dir),
        }


@dataclass(frozen=True)
class CanonicalIdentity:
    """Проверенная clean canonical worktree и его fixed HEAD."""

    git: GitIdentity
    registry_text: str
    registry_sha: str


def _git(root: Path, *arguments: str) -> str:
    """Выполнить read-only Git query и вернуть trimmed stdout."""
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().replace("\n", " ")
        raise ResolverBlocked(f"git {' '.join(arguments)} failed: {detail[-500:]}")
    return completed.stdout.strip()


def _absolute_path(value: str | None, flag: str) -> Path:
    """Проверить обязательную абсолютную path CLI option."""
    if not value:
        raise InvalidRequest(f"{flag} is required")
    path = Path(value)
    if not path.is_absolute():
        raise InvalidRequest(f"{flag} must be absolute")
    return path.resolve()


def _common_dir(root: Path) -> Path:
    """Нормализовать git-common-dir относительно конкретного worktree."""
    raw = Path(_git(root, "rev-parse", "--git-common-dir"))
    return (raw if raw.is_absolute() else root / raw).resolve()


def _branch(root: Path) -> str:
    """Получить полный ref ветки, не принимая detached HEAD за branch."""
    try:
        return _git(root, "symbolic-ref", "--quiet", "HEAD")
    except ResolverBlocked:
        return "HEAD"


def _identity(root: Path) -> GitIdentity:
    """Собрать Git identity и убедиться, что root является worktree."""
    resolved = root.resolve()
    top_level = Path(_git(resolved, "rev-parse", "--show-toplevel")).resolve()
    return GitIdentity(
        root=top_level,
        branch=_branch(top_level),
        sha=_git(top_level, "rev-parse", "HEAD"),
        common_dir=_common_dir(top_level),
    )


def _parse_worktrees(output: str) -> list[tuple[Path, str | None]]:
    """Разобрать porcelain topology в пары worktree path/branch."""
    candidates: list[tuple[Path, str | None]] = []
    current_path: Path | None = None
    current_branch: str | None = None
    for line in output.splitlines() + [""]:
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree ").strip())
            current_branch = None
        elif line.startswith("branch "):
            current_branch = line.removeprefix("branch ").strip()
        elif not line.strip() and current_path is not None:
            candidates.append((current_path, current_branch))
            current_path = None
            current_branch = None
    return candidates


def _validate_canonical(
    candidate: Path, caller: GitIdentity
) -> CanonicalIdentity:
    """Проверить exact scripts branch, common dir, clean state и fixed HEAD."""
    candidate_git = _identity(candidate)
    if candidate_git.branch != "refs/heads/scripts":
        raise ResolverBlocked(
            f"canonical branch must be refs/heads/scripts, got {candidate_git.branch}"
        )
    if candidate_git.common_dir != caller.common_dir:
        raise ResolverBlocked(
            "caller and canonical worktrees do not share one Git common directory"
        )
    tracked_status = _git(
        candidate_git.root, "status", "--porcelain=v1", "--untracked-files=no"
    )
    if tracked_status:
        raise ResolverBlocked("canonical worktree has tracked staged or unstaged changes")
    if not (candidate_git.root / "tools/scripts/resolver.py").is_file():
        raise ResolverBlocked("canonical resolver executable is missing")
    try:
        registry_text = subprocess.run(
            ["git", "-C", str(candidate_git.root), "show", f"{candidate_git.sha}:scripts/REGISTRY.yaml"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if registry_text.returncode != 0:
            raise ResolverBlocked("scripts/REGISTRY.yaml is missing from canonical HEAD")
        registry_document = load_registry_text(registry_text.stdout)
        generated_markdown = subprocess.run(
            [
                "git",
                "-C",
                str(candidate_git.root),
                "show",
                f"{candidate_git.sha}:scripts/REGISTRY.md",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if generated_markdown.returncode != 0:
            raise ResolverBlocked("scripts/REGISTRY.md is missing from canonical HEAD")
        if generated_markdown.stdout != render_markdown(registry_document):
            raise ResolverBlocked("canonical generated Registry Markdown is drifted")
    except RegistryValidationError as exc:
        raise ResolverBlocked(f"canonical Registry is invalid: {exc}") from exc
    registry_sha = _git(
        candidate_git.root,
        "log",
        "-1",
        "--format=%H",
        candidate_git.sha,
        "--",
        "scripts/REGISTRY.yaml",
    )
    if not HEX_SHA.fullmatch(registry_sha):
        raise ResolverBlocked("Registry snapshot has no containing Git commit")
    return CanonicalIdentity(
        git=candidate_git,
        registry_text=registry_text.stdout,
        registry_sha=registry_sha,
    )


def discover_canonical(
    caller: GitIdentity, explicit_root: str | None
) -> CanonicalIdentity:
    """Выбрать canonical root по CLI → env → topology precedence."""
    if explicit_root is not None:
        return _validate_canonical(_absolute_path(explicit_root, "--canonical-root"), caller)
    environment_root = os.environ.get("SCRIPTS_CANONICAL_ROOT")
    if environment_root:
        return _validate_canonical(
            _absolute_path(environment_root, "SCRIPTS_CANONICAL_ROOT"), caller
        )
    topology = _parse_worktrees(_git(caller.root, "worktree", "list", "--porcelain"))
    valid_candidates: list[CanonicalIdentity] = []
    for candidate, branch in topology:
        if branch != "refs/heads/scripts":
            continue
        try:
            valid_candidates.append(_validate_canonical(candidate, caller))
        except ResolverBlocked:
            continue
    if len(valid_candidates) > 1:
        raise ResolverBlocked(
            "ambiguous canonical topology: multiple valid refs/heads/scripts worktrees"
        )
    if valid_candidates:
        return valid_candidates[0]
    raise ResolverBlocked("no valid exact refs/heads/scripts canonical worktree found")


def _as_string_list(request: Mapping[str, Any], field: str) -> list[str]:
    """Проверить request list field и вернуть его значения."""
    value = request.get(field)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise InvalidRequest(f"{field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise InvalidRequest(f"{field} must not contain duplicates")
    return value


def _credential_name(name: object) -> bool:
    """Определить, выглядит ли имя аргумента credential-like."""
    return isinstance(name, str) and SECRET_NAME.search(name) is not None


def _credential_value(value: object) -> bool:
    """Определить очевидный Bearer/JWT credential value."""
    return isinstance(value, str) and (
        BEARER_VALUE.fullmatch(value.strip()) is not None
        or JWT_VALUE.fullmatch(value.strip()) is not None
    )


def _sanitize_value(value: Any, field_name: str = "") -> Any:
    """Рекурсивно удалить credential material из диагностического payload."""
    if _credential_name(field_name) or _credential_value(value):
        return "<redacted>"
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_value(item, str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_value(item, field_name) for item in value]
    return value


def _sanitized_request(request: Mapping[str, Any]) -> dict[str, Any]:
    """Создать безопасную копию request для formal handoff evidence."""
    return _sanitize_value(dict(request))


def _validate_scalar_map(value: Any, field: str) -> None:
    """Проверить request args map на JSON scalar values и отсутствие secrets."""
    if not isinstance(value, dict):
        raise InvalidRequest(f"{field} must be an object")
    scalar_types = (str, int, float, bool)
    for name, item in value.items():
        if _credential_name(name) or _credential_value(item):
            raise InvalidRequest(f"{field} contains credential material")
        if not isinstance(item, scalar_types) and item is not None:
            raise InvalidRequest(f"{field} values must be JSON scalars")


def validate_request(value: Any, cli_mode: str | None) -> dict[str, Any]:
    """Провалидировать exact resolver request schema and mode."""
    if not isinstance(value, dict):
        raise InvalidRequest("request must be a JSON object")
    if set(value) != REQUEST_KEYS:
        unknown = sorted(set(value) - REQUEST_KEYS)
        missing = sorted(REQUEST_KEYS - set(value))
        raise InvalidRequest(f"request keys mismatch; missing={missing}; unknown={unknown}")
    if value.get("schema_version") != REQUEST_SCHEMA:
        raise InvalidRequest(f"schema_version must be {REQUEST_SCHEMA}")
    if cli_mode not in VALID_MODES:
        raise InvalidRequest("CLI mode must be PLAN_RUN or RUN")
    if value.get("mode") != cli_mode:
        raise InvalidRequest("request.mode must match CLI mode")
    for field in ("request_id", "run_id", "change_name_hint"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise InvalidRequest(f"{field} must be a non-empty string")
    if not SAFE_IDENTIFIER.fullmatch(value["request_id"]):
        raise InvalidRequest("request_id contains unsafe path or output characters")
    if not SAFE_IDENTIFIER.fullmatch(value["run_id"]):
        raise InvalidRequest("run_id contains unsafe path or output characters")
    if not KEBAB.fullmatch(value["change_name_hint"]):
        raise InvalidRequest("change_name_hint must be kebab-case")
    for field in ("capabilities", "sources", "required_fields"):
        _as_string_list(value, field)
    if not isinstance(value.get("output_schema_version"), str) or not value[
        "output_schema_version"
    ].strip():
        raise InvalidRequest("output_schema_version must be a non-empty string")
    if not isinstance(value.get("primary_artifact_pattern"), str) or not value[
        "primary_artifact_pattern"
    ].strip():
        raise InvalidRequest("primary_artifact_pattern must be a non-empty string")
    _validate_scalar_map(value.get("required_args"), "required_args")
    _validate_scalar_map(value.get("optional_args"), "optional_args")
    if set(value["required_args"]) & set(value["optional_args"]):
        raise InvalidRequest("required_args and optional_args must not overlap")
    if value.get("zero_write_required") is not True:
        raise InvalidRequest("zero_write_required must be true")
    for field in ("explicit_script", "owning_change_id"):
        if value[field] is not None and (
            not isinstance(value[field], str) or not value[field].strip()
        ):
            raise InvalidRequest(f"{field} must be a string or null")
        if value[field] is not None and _credential_value(value[field]):
            raise InvalidRequest(f"{field} contains credential material")
    if value["owning_change_id"] is not None and not KEBAB.fullmatch(
        value["owning_change_id"]
    ):
        raise InvalidRequest("owning_change_id must be kebab-case")
    for field in (
        "change_name_hint",
        "output_schema_version",
        "primary_artifact_pattern",
    ):
        if _credential_value(value[field]):
            raise InvalidRequest(f"{field} contains credential material")
    return value


def _safe_request_ids(raw: Any) -> tuple[str | None, str | None]:
    """Извлечь identifiers из повреждённого JSON без повторного parsing path."""
    if not isinstance(raw, dict):
        return None, None
    request_id = raw.get("request_id")
    run_id = raw.get("run_id")
    return (
        request_id if isinstance(request_id, str) and SAFE_IDENTIFIER.fullmatch(request_id) else None,
        run_id if isinstance(run_id, str) and SAFE_IDENTIFIER.fullmatch(run_id) else None,
    )


def _entry_args_covered(entry: Mapping[str, Any], request: Mapping[str, Any]) -> bool:
    """Проверить, что request передал все required args выбранного row."""
    values = set(request["required_args"]) | set(request["optional_args"])
    return set(entry.get("required_args", {})) <= values


def _compatible(entry: Mapping[str, Any], request: Mapping[str, Any]) -> bool:
    """Проверить automatic capability/source/field/output compatibility."""
    if not _entry_args_covered(entry, request):
        return False
    if not set(request["capabilities"]) <= set(entry.get("capabilities", [])):
        return False
    if not set(request["sources"]) <= set(entry.get("sources", [])):
        return False
    if not set(request["required_fields"]) <= set(entry.get("provided_fields", [])):
        return False
    if request["output_schema_version"] != entry.get("output_schema_version"):
        return False
    if request["primary_artifact_pattern"] != entry.get("primary_artifact_pattern"):
        return False
    effects = set(entry.get("side_effects", []))
    return request["zero_write_required"] and "READ_ONLY" in effects and not {
        "EXTERNAL_WRITE",
        "PRODUCTION_WRITE",
    } & effects


def _selection(entry: Mapping[str, Any]) -> dict[str, str]:
    """Сформировать compact selection evidence для stdout result."""
    return {
        "registry_id": str(entry["id"]),
        "collector_path": str(entry["path"]),
    }


def _topological_order(
    selected: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]] | None:
    """Построить deterministic topological order по `compose_with`.

    Returns:
        Ordered selected rows, либо `None`, если selected row ссылается на
        predecessor вне выбранного набора.

    Raises:
        ResolverBlocked: если dependency graph содержит self-reference,
            duplicate dependency или cycle.
    """
    by_id = {str(entry["id"]): entry for entry in selected}
    dependencies: dict[str, set[str]] = {}
    for entry in selected:
        entry_id = str(entry["id"])
        raw_dependencies = entry.get("compose_with", [])
        if not isinstance(raw_dependencies, list):
            raise ResolverBlocked(f"compose_with is not a list for {entry_id}")
        if any(not isinstance(item, str) for item in raw_dependencies):
            raise ResolverBlocked(f"compose_with has non-string dependency for {entry_id}")
        if len(raw_dependencies) != len(set(raw_dependencies)):
            raise ResolverBlocked(f"compose_with has duplicate dependencies for {entry_id}")
        dependency_ids = {str(item) for item in raw_dependencies}
        if entry_id in dependency_ids:
            raise ResolverBlocked(f"compose_with self-reference for {entry_id}")
        if not dependency_ids <= set(by_id):
            return None
        dependencies[entry_id] = dependency_ids

    ordered: list[Mapping[str, Any]] = []
    remaining = set(by_id)
    while remaining:
        ready = sorted(
            entry_id
            for entry_id in remaining
            if dependencies[entry_id].isdisjoint(remaining)
        )
        if not ready:
            raise ResolverBlocked("compose_with dependency cycle detected")
        for entry_id in ready:
            ordered.append(by_id[entry_id])
            remaining.remove(entry_id)
    return ordered


def _compose_plan(
    entries: Sequence[Mapping[str, Any]], request: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Найти deterministic ordered acyclic child plan without semantic merge."""
    composable = [
        entry
        for entry in sorted(entries, key=lambda item: str(item["id"]))
        if entry.get("resolution_enabled") is True
        and entry.get("composable") is True
        and _entry_args_covered(entry, request)
        and set(request["sources"]) <= set(entry.get("sources", []))
        and request["output_schema_version"] == entry.get("output_schema_version")
        and request["primary_artifact_pattern"] == entry.get("primary_artifact_pattern")
    ]
    for size in range(2, len(composable) + 1):
        for selected in combinations(composable, size):
            fields: set[str] = set()
            capabilities: set[str] = set()
            sources: set[str] = set()
            for entry in selected:
                fields.update(entry.get("provided_fields", []))
                capabilities.update(entry.get("capabilities", []))
                sources.update(entry.get("sources", []))
            if not set(request["required_fields"]) <= fields:
                continue
            if not set(request["capabilities"]) <= capabilities:
                continue
            if not set(request["sources"]) <= sources:
                continue
            ordered_entries = _topological_order(selected)
            if ordered_entries is None:
                continue
            children = [
                {
                    "order": order,
                    "registry_id": entry["id"],
                    "collector_path": entry["path"],
                    "args": {
                        key: request["required_args"].get(
                            key, request["optional_args"].get(key)
                        )
                        for key in sorted(
                            set(entry.get("required_args", {}))
                            | set(entry.get("optional_args", {}))
                        )
                        if key in request["required_args"]
                        or key in request["optional_args"]
                    },
                    "outputs": [entry["primary_artifact_pattern"]],
                    "required": True,
                }
                for order, entry in enumerate(ordered_entries, start=1)
            ]
            return {"schema_version": COMPOSE_SCHEMA, "children": children}
    return None


def _formal_change(
    request: Mapping[str, Any],
    caller: GitIdentity,
    canonical: CanonicalIdentity,
) -> dict[str, Any]:
    """Сформировать deterministic formal-change handoff для missing capability."""
    owner_change_id = request.get("owning_change_id")
    formal_type = "EXTEND" if owner_change_id else "CREATE"
    owner_exists = False
    if isinstance(owner_change_id, str):
        owner_exists = (
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(canonical.git.root),
                    "cat-file",
                    "-e",
                    f"{canonical.git.sha}:openspec/changes/{owner_change_id}/proposal.md",
                ],
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
    command = (
        f"/opsx-update {owner_change_id}"
        if formal_type == "EXTEND" and owner_exists
        else f"/opsx-ff {request['change_name_hint']}"
    )
    contract_payload = _sanitized_request(request)
    contract = json.dumps(contract_payload, ensure_ascii=False, sort_keys=True)
    prompt = (
        f"{command}\n"
        f"workspace={caller.root}\n"
        f"formal_type={formal_type}\n"
        f"request_contract={contract}\n"
        "safety_constraints=NO operational collector/registry writes; "
        "preserve READ_ONLY, immutable artifact and checksum gates; "
        "apply=PROHIBITED until separately authorized GO."
    )
    return {
        "schema_version": FORMAL_SCHEMA,
        "outcome": "FORMAL_CHANGE_REQUIRED",
        "run_id": request["run_id"],
        "request_id": request["request_id"],
        "formal_type": formal_type,
        "command": command,
        "change_name": request["change_name_hint"],
        "owner_change_id": owner_change_id,
        "reason": "No compatible resolution-enabled collector covers the request contract.",
        "evidence": [
            {
                "path": "scripts/REGISTRY.yaml",
                "line": 1,
                "detail": "automatic capability/field/output coverage is insufficient",
            }
        ],
        "request_contract": contract_payload,
        "constraints": [
            "No operational collector write",
            "Preserve READ_ONLY_NO_MUTATION",
            "Preserve immutable artifact and checksum gates",
        ],
        "pasteable_prompt": prompt,
        "created_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def _base_result(
    mode: str | None,
    request_id: str | None,
    run_id: str | None,
    caller: GitIdentity | None,
) -> dict[str, Any]:
    """Создать полный result envelope с безопасными nullable fields."""
    return {
        "schema_version": RESULT_SCHEMA,
        "mode": mode,
        "request_id": request_id,
        "run_id": run_id,
        "caller": caller.as_result() if caller else None,
        "outcome": "BLOCKED",
        "execution_sha": None,
        "registry_sha": None,
        "canonical_worktree": None,
        "selection": [],
        "selection_mode": "NONE",
        "compose_plan": None,
        "formal_change": None,
        "error": None,
        "operational_write_path": False,
    }


def resolve(
    mode: str,
    request: Mapping[str, Any],
    caller_root: Path,
    canonical_root: str | None = None,
) -> dict[str, Any]:
    """Выполнить read-only resolution и вернуть machine result."""
    caller = _identity(caller_root)
    canonical = discover_canonical(caller, canonical_root)
    registry = load_registry_text(canonical.registry_text)
    result = _base_result(mode, request["request_id"], request["run_id"], caller)
    result["execution_sha"] = canonical.git.sha
    result["registry_sha"] = canonical.registry_sha
    result["canonical_worktree"] = canonical.git.as_result()
    entries = registry["entries"]
    explicit_script = request.get("explicit_script")
    if explicit_script is not None:
        matches = [
            entry
            for entry in entries
            if entry.get("explicit_invocation_enabled") is True
            and explicit_script in {entry.get("id"), entry.get("path")}
        ]
        if len(matches) != 1:
            result["error"] = {
                "code": "EXPLICIT_SELECTION_BLOCKED",
                "message": "explicit_script must select exactly one safety-enabled row",
            }
            return result
        entry = matches[0]
        if not _compatible_explicit(entry, request):
            result["error"] = {
                "code": "EXPLICIT_SAFETY_VALIDATION_FAILED",
                "message": "explicit row failed args, output, READ_ONLY or artifact validation",
            }
            return result
        result["outcome"] = "REUSE"
        result["selection"] = [_selection(entry)]
        result["selection_mode"] = "EXPLICIT"
        return result
    candidates = [
        entry
        for entry in entries
        if entry.get("resolution_enabled") is True and _compatible(entry, request)
    ]
    if len(candidates) == 1:
        result["outcome"] = "REUSE"
        result["selection"] = [_selection(candidates[0])]
        result["selection_mode"] = "AUTOMATIC"
        return result
    compose_plan = _compose_plan(entries, request)
    if compose_plan is not None:
        result["outcome"] = "COMPOSE"
        result["compose_plan"] = compose_plan
        result["selection_mode"] = "AUTOMATIC"
        return result
    if len(candidates) > 1:
        result["error"] = {
            "code": "AMBIGUOUS_AUTOMATIC_RESOLUTION",
            "message": "multiple compatible registry rows have no unique plan",
            "candidates": [str(entry["id"]) for entry in candidates],
        }
        result["outcome"] = "BLOCKED"
        result["selection_mode"] = "NONE"
        return result
    result["outcome"] = "FORMAL_CHANGE_REQUIRED"
    result["formal_change"] = _formal_change(request, caller, canonical)
    result["selection_mode"] = "NONE"
    return result


def _compatible_explicit(
    entry: Mapping[str, Any], request: Mapping[str, Any]
) -> bool:
    """Проверить explicit row без допуска к automatic matching."""
    if not _entry_args_covered(entry, request):
        return False
    if request["output_schema_version"] != entry.get("output_schema_version"):
        return False
    if not fnmatch(
        request["primary_artifact_pattern"], str(entry.get("primary_artifact_pattern"))
    ) and not fnmatch(
        str(entry.get("primary_artifact_pattern")), request["primary_artifact_pattern"]
    ):
        return False
    effects = set(entry.get("side_effects", []))
    return request["zero_write_required"] and "READ_ONLY" in effects


def _emit(result: Mapping[str, Any]) -> None:
    """Вывести ровно один compact JSON result на stdout."""
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def _exit_code(outcome: str, malformed: bool = False, unexpected: bool = False) -> int:
    """Преобразовать outcome в фиксированный CLI exit code."""
    if unexpected:
        return 30
    if malformed:
        return 2
    return {"REUSE": 0, "COMPOSE": 0, "FORMAL_CHANGE_REQUIRED": 10, "BLOCKED": 20}[
        outcome
    ]


def main(argv: list[str] | None = None) -> int:
    """Запустить PLAN_RUN/RUN resolver с machine-readable stdout contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?")
    parser.add_argument("--request-file", type=str)
    parser.add_argument("--caller-root", type=str)
    parser.add_argument("--canonical-root", type=str)
    args = parser.parse_args(argv)
    mode = args.mode if isinstance(args.mode, str) else None
    result = _base_result(mode, None, None, None)
    try:
        if mode not in VALID_MODES:
            raise InvalidRequest("mode must be PLAN_RUN or RUN")
        request_path = _absolute_path(args.request_file, "--request-file")
        caller_root = _absolute_path(args.caller_root, "--caller-root")
        raw_text = request_path.read_text(encoding="utf-8")
        try:
            raw_request = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            request_id, run_id = _safe_request_ids(None)
            result = _base_result(mode, request_id, run_id, None)
            result["error"] = {"code": "INVALID_REQUEST", "message": f"invalid JSON: {exc.msg}"}
            _emit(result)
            return 2
        request_id, run_id = _safe_request_ids(raw_request)
        result = _base_result(mode, request_id, run_id, None)
        request = validate_request(raw_request, mode)
        caller = _identity(caller_root)
        result = resolve(mode, request, caller.root, args.canonical_root)
        _emit(result)
        return _exit_code(result["outcome"])
    except (InvalidRequest, OSError) as exc:
        result["error"] = {"code": "INVALID_REQUEST", "message": str(exc)}
        _emit(result)
        return 2
    except (ResolverBlocked, RegistryValidationError) as exc:
        result["error"] = {"code": "BLOCKED", "message": str(exc)}
        _emit(result)
        return 20
    except Exception as exc:  # noqa: BLE001
        result["error"] = {"code": "INTERNAL_ERROR", "message": str(exc)}
        _emit(result)
        return 30


if __name__ == "__main__":
    raise SystemExit(main())
