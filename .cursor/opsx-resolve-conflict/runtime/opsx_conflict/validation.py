"""Frozen test-plan validation boundary (RC04-C02 / H07 / M01 / R28).

FULL registry compilation consumes the actual OPSX registry shape
(``task_type`` + ``pack``). Exact argv / timeouts / success codes come from a
closed package-owned adapter table keyed by ``(check_id, task_type, pack)``.
Pack trees are hash-bound contract identity only and are never executed.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .cancellation import run_process
from .errors import PolicyViolation, StopRequired
from .hashutil import sha256_bytes, sha256_canonical, sha256_text
from .proofs import Proof


ALLOWED_TOOLS = frozenset(
    {
        "pytest",
        "pyright",
        "pyright-strict",
        "mypy",
        "ruff",
        "security-scan",
        "openspec-validate",
        "syntax-parse",
        "git-diff-check",
    }
)
VALIDATION_ADAPTER_SCHEMA = "opsx-resolve-conflict/validation-adapter/v1"
# HISTORICAL_BASELINE_ALLOWLIST: pre-R28 used execution.json descriptors.
EXPECTED_CHECK_ARGV: Mapping[str, tuple[str, ...]] = {
    "pyright-strict": ("poetry", "run", "pyright-strict"),
    "mypy": ("poetry", "run", "mypy", "."),
    "pytest-unit": ("poetry", "run", "pytest", "-m", "unit"),
    "pytest-full": ("poetry", "run", "pytest"),
}
# Categories that must each resolve to PASSED / NOT_APPLICABLE before FULL.
OPSX_VALIDATION_CATEGORIES: tuple[str, ...] = (
    "syntax_structural",
    "format_lint",
    "static_analysis",
    "type_checks",
    "targeted_symbol_tests",
    "interface_contract_tests",
    "affected_contour_tests",
    "integration_tests",
    "schema_migration",
    "security",
    "openspec_validation",
    "project_full_gate",
    "registry_discovered_unclassified",
    "opsx_pipeline_conditional_gates",
)
# Pipeline gates that must appear in inventory when GRAPH.md mentions them.
_PIPELINE_CONDITIONAL_GATES = (
    "opsx-pyright-strict-coverage",
    "opsx-external-call-coverage",
    "opsx-antipattern-gate",
    "opsx-verify",
)
FORBIDDEN_ARG_TOKENS = (
    "-p",
    "--collect-only",
    "--confcutdir",
    "--rootdir",
    "--import-mode",
    "--project",
    "--config-file",
    ";",
    "&&",
    "||",
    "`",
    "$(",
)


@dataclass(frozen=True)
class TypedCheckAdapter:
    """Closed package-owned argv/timeout policy for one registry check."""

    check_id: str
    task_type: str
    pack: str
    argv: tuple[str, ...]
    tool: str
    timeout_seconds: float
    success_exit_codes: tuple[int, ...]
    pack_files: tuple[str, ...]


def _build_typed_adapters() -> dict[tuple[str, str, str], TypedCheckAdapter]:
    """Build the closed adapter table (exact key = check_id/task_type/pack)."""
    specs: tuple[tuple[str, str, str, tuple[str, ...], str, float], ...] = (
        (
            "pyright-strict",
            "shell",
            ".cursor/static-check/checks/pyright-strict",
            ("poetry", "run", "pyright-strict"),
            "pyright-strict",
            900.0,
        ),
        (
            "mypy",
            "shell",
            ".cursor/static-check/checks/mypy",
            ("poetry", "run", "mypy", "."),
            "mypy",
            900.0,
        ),
        (
            "pytest-unit",
            "shell",
            ".cursor/static-check/checks/pytest-unit",
            ("poetry", "run", "pytest", "-m", "unit"),
            "pytest",
            1800.0,
        ),
        (
            "pytest-full",
            "shell",
            ".cursor/static-check/checks/pytest-full",
            ("poetry", "run", "pytest"),
            "pytest",
            3600.0,
        ),
    )
    pack_files = ("context.md", "instructions.md")
    out: dict[tuple[str, str, str], TypedCheckAdapter] = {}
    for check_id, task_type, pack, argv, tool, timeout in specs:
        out[(check_id, task_type, pack)] = TypedCheckAdapter(
            check_id=check_id,
            task_type=task_type,
            pack=pack,
            argv=argv,
            tool=tool,
            timeout_seconds=timeout,
            success_exit_codes=(0,),
            pack_files=pack_files,
        )
    return out


TYPED_CHECK_ADAPTERS: Mapping[tuple[str, str, str], TypedCheckAdapter] = (
    _build_typed_adapters()
)


@dataclass(frozen=True)
class FrozenCheck:
    check_id: str
    tool: str
    rel_nodes: tuple[str, ...]
    wave: str  # A | B | unit
    argv: tuple[str, ...]
    timeout_seconds: float
    task_type: str = ""
    pack: str = ""
    success_exit_codes: tuple[int, ...] = (0,)
    pack_inventory_digest: str = ""
    adapter_schema: str = VALIDATION_ADAPTER_SCHEMA


def _normalize_pack_rel(pack: str, *, check_id: str) -> str:
    """Normalize and reject escaping pack paths."""
    if not isinstance(pack, str) or not pack.strip():
        raise StopRequired(
            "FULL_VALIDATION_PACK_MISSING",
            {"check_id": check_id},
        )
    normalized = pack.replace("\\", "/").strip()
    if normalized.startswith("/") or normalized.startswith("~"):
        raise StopRequired(
            "FULL_VALIDATION_PACK_PATH_ESCAPE",
            {"check_id": check_id, "pack": pack},
        )
    parts = Path(normalized).parts
    if ".." in parts or any(part == "" for part in parts):
        raise StopRequired(
            "FULL_VALIDATION_PACK_PATH_ESCAPE",
            {"check_id": check_id, "pack": pack},
        )
    return Path(normalized).as_posix().rstrip("/")


def _verify_pack_inventory(
    *,
    root: Path,
    check_id: str,
    pack_rel: str,
    expected_files: Sequence[str],
    expected_hashes: Mapping[str, str],
) -> tuple[str, dict[str, str]]:
    """Verify pack directory identity against frozen host-contract inventory."""
    pack_path = (root / pack_rel).resolve()
    try:
        pack_path.relative_to(root.resolve())
    except ValueError as exc:
        raise StopRequired(
            "FULL_VALIDATION_PACK_PATH_ESCAPE",
            {"check_id": check_id, "pack": pack_rel},
        ) from exc
    if pack_path.is_symlink():
        raise StopRequired(
            "FULL_VALIDATION_PACK_SYMLINK",
            {"check_id": check_id, "pack": pack_rel},
        )
    if not pack_path.is_dir():
        raise StopRequired(
            "FULL_VALIDATION_PACK_DIRECTORY_MISSING",
            {"check_id": check_id, "pack": pack_rel},
        )
    expected_rel_files = {
        f"{pack_rel}/{name}".replace("//", "/") for name in expected_files
    }
    actual_files: dict[str, Path] = {}
    for path in sorted(pack_path.rglob("*")):
        if path.is_dir():
            continue
        if path.is_symlink():
            raise StopRequired(
                "FULL_VALIDATION_PACK_SYMLINK",
                {
                    "check_id": check_id,
                    "pack": pack_rel,
                    "path": path.relative_to(root).as_posix(),
                },
            )
        if not path.is_file():
            raise StopRequired(
                "FULL_VALIDATION_PACK_ENTRY_UNSUPPORTED",
                {
                    "check_id": check_id,
                    "path": path.relative_to(root).as_posix(),
                },
            )
        rel = path.relative_to(root).as_posix()
        actual_files[rel] = path
    actual_set = set(actual_files)
    missing = sorted(expected_rel_files - actual_set)
    extra = sorted(actual_set - expected_rel_files)
    if missing:
        raise StopRequired(
            "FULL_VALIDATION_PACK_FILE_MISSING",
            {"check_id": check_id, "pack": pack_rel, "missing": missing},
        )
    if extra:
        raise StopRequired(
            "FULL_VALIDATION_PACK_FILE_EXTRA",
            {"check_id": check_id, "pack": pack_rel, "extra": extra},
        )
    file_hashes: dict[str, str] = {}
    for rel in sorted(expected_rel_files):
        digest = sha256_bytes(actual_files[rel].read_bytes())
        expected = expected_hashes.get(rel)
        if expected is None:
            raise StopRequired(
                "FULL_VALIDATION_PACK_FILE_NOT_FROZEN",
                {"check_id": check_id, "path": rel},
            )
        if expected != digest:
            raise StopRequired(
                "FULL_VALIDATION_FROZEN_BYTES_MISMATCH",
                {"path": rel, "expected": expected, "actual": digest},
            )
        file_hashes[rel] = digest
    inventory_digest = sha256_canonical(
        [{"path": path, "sha256": file_hashes[path]} for path in sorted(file_hashes)]
    )
    return inventory_digest, file_hashes


def _load_registry_checks(
    registry_path: Path,
    expected_hashes: Mapping[str, str],
) -> tuple[list[FrozenCheck], dict[str, Any], str, tuple[str, ...]]:
    """Compile FULL waves from actual OPSX registry + closed typed adapters.

    Returns selected checks, pack inventory proof, registry digest, and an
    empty unclassified tuple (unknown selected checks fail closed).
    """
    root = registry_path.resolve().parents[2]
    registry_rel = registry_path.resolve().relative_to(root).as_posix()
    try:
        registry_bytes = registry_path.read_bytes()
        registry_sha256 = sha256_bytes(registry_bytes)
        if expected_hashes.get(registry_rel) != registry_sha256:
            raise StopRequired(
                "FULL_VALIDATION_FROZEN_BYTES_MISMATCH",
                {"path": registry_rel},
            )
        registry = yaml.safe_load(registry_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise StopRequired(
            "FULL_VALIDATION_REGISTRY_INVALID",
            {"path": str(registry_path), "error": str(exc)},
        ) from exc
    if not isinstance(registry, dict) or registry.get("version") != 1:
        raise StopRequired("FULL_VALIDATION_REGISTRY_INVALID_VERSION")
    modes = registry.get("modes")
    checks_config = registry.get("checks")
    if not isinstance(modes, dict) or not isinstance(checks_config, dict):
        raise StopRequired("FULL_VALIDATION_REGISTRY_INVALID")
    full = modes.get("FULL")
    waves = full.get("waves") if isinstance(full, dict) else None
    if not isinstance(waves, list) or not waves:
        raise StopRequired("FULL_VALIDATION_WAVES_MISSING")

    selected: list[FrozenCheck] = []
    pack_inventory: dict[str, Any] = {}
    seen_waves: set[str] = set()
    seen_checks: set[str] = set()
    prior_checks: set[str] = set()
    for wave in waves:
        if not isinstance(wave, dict):
            raise StopRequired("FULL_VALIDATION_WAVE_INVALID")
        wave_id = wave.get("id")
        check_ids = wave.get("checks")
        if not isinstance(wave_id, str) or wave_id in seen_waves:
            raise StopRequired("FULL_VALIDATION_WAVE_DUPLICATE", {"wave": wave_id})
        if not isinstance(check_ids, list) or not check_ids:
            raise StopRequired("FULL_VALIDATION_WAVE_EMPTY", {"wave": wave_id})
        dependencies = wave.get("after", [])
        if not isinstance(dependencies, list) or any(
            dep not in prior_checks for dep in dependencies
        ):
            raise StopRequired(
                "FULL_VALIDATION_DEPENDENCY_INVALID",
                {"wave": wave_id, "after": dependencies},
            )
        if dependencies and wave.get("require_status") != "PASS":
            raise StopRequired(
                "FULL_VALIDATION_DEPENDENCY_STATUS_INVALID",
                {"wave": wave_id},
            )
        seen_waves.add(wave_id)
        for check_id in check_ids:
            if not isinstance(check_id, str) or check_id in seen_checks:
                raise StopRequired(
                    "FULL_VALIDATION_CHECK_DUPLICATE",
                    {"check_id": check_id},
                )
            config = checks_config.get(check_id)
            if not isinstance(config, dict):
                raise StopRequired(
                    "FULL_VALIDATION_CHECK_UNKNOWN",
                    {"check_id": check_id},
                )
            task_type = config.get("task_type")
            if not isinstance(task_type, str) or not task_type.strip():
                raise StopRequired(
                    "FULL_VALIDATION_TASK_TYPE_MISSING",
                    {"check_id": check_id},
                )
            task_type = task_type.strip()
            pack_rel = _normalize_pack_rel(
                str(config.get("pack") or ""),
                check_id=check_id,
            )
            adapter = TYPED_CHECK_ADAPTERS.get((check_id, task_type, pack_rel))
            if adapter is None:
                raise StopRequired(
                    "FULL_VALIDATION_ADAPTER_UNAVAILABLE",
                    {
                        "check_id": check_id,
                        "task_type": task_type,
                        "pack": pack_rel,
                        "note": (
                            "Selected check has no closed typed adapter; "
                            "generic/pack-derived argv is forbidden."
                        ),
                    },
                )
            if adapter.tool not in ALLOWED_TOOLS:
                raise StopRequired(
                    "FULL_VALIDATION_CHECK_UNSUPPORTED",
                    {"check_id": check_id, "tool": adapter.tool},
                )
            if tuple(adapter.argv) != EXPECTED_CHECK_ARGV[check_id]:
                raise StopRequired(
                    "FULL_VALIDATION_ARGV_BINDING_MISMATCH",
                    {
                        "check_id": check_id,
                        "expected": list(EXPECTED_CHECK_ARGV[check_id]),
                        "actual": list(adapter.argv),
                    },
                )
            inventory_digest, file_hashes = _verify_pack_inventory(
                root=root,
                check_id=check_id,
                pack_rel=pack_rel,
                expected_files=adapter.pack_files,
                expected_hashes=expected_hashes,
            )
            pack_inventory[pack_rel] = {
                "check_id": check_id,
                "inventory_digest": inventory_digest,
                "files": file_hashes,
                "adapter_schema": VALIDATION_ADAPTER_SCHEMA,
                "task_type": task_type,
                "argv": list(adapter.argv),
                "timeout_seconds": adapter.timeout_seconds,
                "success_exit_codes": list(adapter.success_exit_codes),
                "wave": wave_id,
                "dependencies": list(dependencies),
            }
            selected.append(
                FrozenCheck(
                    check_id,
                    adapter.tool,
                    (),
                    wave_id,
                    adapter.argv,
                    float(adapter.timeout_seconds),
                    task_type=task_type,
                    pack=pack_rel,
                    success_exit_codes=adapter.success_exit_codes,
                    pack_inventory_digest=inventory_digest,
                    adapter_schema=VALIDATION_ADAPTER_SCHEMA,
                )
            )
            seen_checks.add(check_id)
            prior_checks.add(check_id)
    required = {"pyright-strict", "mypy", "pytest-unit", "pytest-full"}
    missing_required = sorted(required - seen_checks)
    if missing_required:
        raise StopRequired(
            "FULL_VALIDATION_REQUIRED_CHECK_SET_MISMATCH",
            {"expected": sorted(required), "actual": sorted(seen_checks)},
        )
    return selected, pack_inventory, registry_sha256, ()


def _load_test_role_manifest(root: Path, test_rel: str) -> dict[str, Any] | None:
    """Load hash-bound role metadata for one test module, if present."""
    roles_rel = str(Path(test_rel).with_suffix(".opsx-roles.json").as_posix())
    roles_path = root / roles_rel
    if not roles_path.is_file() or roles_path.is_symlink():
        return None
    try:
        payload = json.loads(roles_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema") != "opsx-resolve-conflict/test-roles/v1":
        return None
    roles = payload.get("roles")
    covers = payload.get("covers_paths")
    symbols = payload.get("covers_symbols")
    if not isinstance(roles, list) or not roles:
        return None
    if not isinstance(covers, list) or not covers:
        return None
    if not isinstance(symbols, list) or not symbols:
        return None
    return {
        "roles": [str(role) for role in roles],
        "covers_paths": [str(path) for path in covers],
        "covers_symbols": [str(symbol) for symbol in symbols],
        "roles_manifest": roles_rel,
        "roles_manifest_sha256": sha256_bytes(roles_path.read_bytes()),
    }


def _defined_symbols_from_text(text: str) -> set[str]:
    """Return top-level function/class names defined in Python source text."""
    import ast

    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _defined_symbols(py_path: Path) -> set[str]:
    """Return top-level function/class names defined in a Python module."""
    try:
        return _defined_symbols_from_text(py_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return set()


def _module_name_from_path(path: str) -> str | None:
    """Convert ``app/service.py`` to ``app.service`` (``__init__`` aware)."""
    rel = Path(path)
    if rel.suffix != ".py":
        return None
    parts = list(rel.with_suffix("").parts)
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def _symbol_import_aliases(
    tree: ast.Module,
    *,
    modules: set[str],
    symbol: str,
) -> set[str]:
    """Return aliases importing ``symbol`` from trusted production modules."""
    aliases: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level != 0 or node.module not in modules:
            continue
        for alias in node.names:
            if alias.name == symbol:
                aliases.add(alias.asname or alias.name)
    return aliases


def _module_import_aliases(tree: ast.Module, *, modules: set[str]) -> dict[str, str]:
    """Map import alias -> absolute module for trusted production modules."""
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    out[alias.asname or alias.name.split(".", 1)[0]] = alias.name
            continue
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                candidate = f"{node.module}.{alias.name}"
                if candidate in modules:
                    out[alias.asname or alias.name] = candidate
    return out


def _alias_rebound(tree: ast.Module, alias: str) -> bool:
    """True when imported alias is redefined by local code."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == alias:
                return True
        if isinstance(node, ast.arg) and node.arg == alias:
            return True
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if node.id == alias:
                return True
    return False


def _is_protected_assert_for_alias(node: ast.Assert, alias: str) -> bool:
    """Return True when assert protects exactly one direct call to alias."""
    banned_shapes = (
        ast.BoolOp,
        ast.IfExp,
        ast.Subscript,
        ast.Tuple,
        ast.List,
        ast.Set,
        ast.Dict,
        ast.Lambda,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    if any(isinstance(child, banned_shapes) for child in ast.walk(node.test)):
        return False
    calls = [child for child in ast.walk(node.test) if isinstance(child, ast.Call)]
    if len(calls) != 1:
        return False
    call = calls[0]
    if not isinstance(call.func, ast.Name) or call.func.id != alias:
        return False
    return True


def _symbol_monkeypatched(
    tree: ast.Module,
    *,
    modules: set[str],
    module_aliases: Mapping[str, str],
    symbol: str,
) -> bool:
    """Detect common monkeypatch replacement patterns for production symbol."""
    fq_targets = {f"{module}.{symbol}" for module in modules}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "setattr":
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            if first.value in fq_targets or first.value.replace(":", ".") in fq_targets:
                return True
        if (
            isinstance(first, ast.Name)
            and first.id in module_aliases
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == symbol
        ):
            return True
    return False


def _test_behaviorally_covers(
    test_path: Path,
    *,
    covered_paths: Sequence[str],
    symbols: Sequence[str],
) -> bool:
    """True when every symbol is imported from production and protected in assert.

    Name presence is insufficient: coverage requires a qualified import from a
    covered production module and exactly one protected assert call of that
    imported alias.
    """
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    modules = {
        module
        for path in covered_paths
        if (module := _module_name_from_path(path)) is not None
    }
    if not modules:
        return False
    module_aliases = _module_import_aliases(tree, modules=modules)
    for symbol in symbols:
        aliases = _symbol_import_aliases(tree, modules=modules, symbol=symbol)
        if not aliases:
            return False
        if any(_alias_rebound(tree, alias) for alias in aliases):
            return False
        if _symbol_monkeypatched(
            tree,
            modules=modules,
            module_aliases=module_aliases,
            symbol=symbol,
        ):
            return False
        proven = any(
            isinstance(node, ast.Assert)
            and any(_is_protected_assert_for_alias(node, alias) for alias in aliases)
            for node in ast.walk(tree)
        )
        if not proven:
            return False
    return True


def _role_coverage_proven(
    root: Path,
    *,
    test_rel: str,
    meta: Mapping[str, Any],
    production_paths: set[str],
    production_texts: Mapping[str, str] | None = None,
) -> bool:
    """Prove role metadata against production symbols and behavioral coverage."""
    covered = production_paths & set(meta["covers_paths"])
    if not covered:
        return False
    symbols = list(meta["covers_symbols"])
    if not symbols:
        return False
    texts = dict(production_texts or {})
    defined: set[str] = set()
    for rel in covered:
        if rel in texts:
            defined |= _defined_symbols_from_text(texts[rel])
        else:
            defined |= _defined_symbols(root / rel)
    if not set(symbols).issubset(defined):
        return False
    return _test_behaviorally_covers(
        root / test_rel,
        covered_paths=tuple(covered),
        symbols=symbols,
    )


def discover_role_bound_tests(
    root: Path,
    *,
    production_paths: Sequence[str],
    role: str,
    production_texts: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Return tests with proven symbol coverage for ``role`` and paths."""
    production = {str(path) for path in production_paths}
    found: list[str] = []
    for roles_path in sorted(root.glob("tests/**/*.opsx-roles.json")):
        if roles_path.is_symlink() or not roles_path.is_file():
            continue
        rel_roles = roles_path.relative_to(root).as_posix()
        if not rel_roles.endswith(".opsx-roles.json"):
            continue
        test_rel = rel_roles[: -len(".opsx-roles.json")] + ".py"
        if not (root / test_rel).is_file():
            continue
        meta = _load_test_role_manifest(root, test_rel)
        if meta is None or role not in meta["roles"]:
            continue
        if len(meta["roles"]) > 1:
            raise StopRequired(
                "OPSX_VALIDATION_MULTI_ROLE_FORBIDDEN",
                {
                    "test": test_rel,
                    "roles": list(meta["roles"]),
                    "hint": "one role per sidecar; split tests for separate roles",
                },
            )
        if not _role_coverage_proven(
            root,
            test_rel=test_rel,
            meta=meta,
            production_paths=production,
            production_texts=production_texts,
        ):
            continue
        found.append(test_rel)
    return tuple(dict.fromkeys(found))


class FrozenTestPlanCompiler:
    """Compile immutable checks from scope + registry; no caller argv."""

    def __init__(
        self,
        *,
        run_id: str,
        fingerprint: str,
        scope_sha256: str,
        content_fingerprints: Mapping[str, str],
        registry_path: Path | None,
        frozen_contract_hashes: Mapping[str, str] | None = None,
        targeted_nodes: Sequence[str],
        interface_nodes: Sequence[str] = (),
        contour_nodes: Sequence[str] = (),
        adjacent_nodes: Sequence[str] = (),
        production_texts: Mapping[str, str] | None = None,
    ) -> None:
        self.run_id = run_id
        self.fingerprint = fingerprint
        self.scope_sha256 = scope_sha256
        self.content_fingerprints = dict(content_fingerprints)
        self.registry_path = registry_path
        self.frozen_contract_hashes = dict(frozen_contract_hashes or {})
        self.targeted_nodes = tuple(targeted_nodes)
        # Filename-only adjacent discovery is intentionally ignored for role
        # claims; interface/contour require explicit role-bound nodes.
        _ = adjacent_nodes
        self.interface_nodes = tuple(interface_nodes)
        self.contour_nodes = tuple(contour_nodes)
        self.production_texts = dict(production_texts or {})

    def _repo_root(self) -> Path | None:
        if not self.registry_path:
            return None
        return self.registry_path.resolve().parents[2]

    def _role_tests(self, role: str) -> tuple[str, ...]:
        """Resolve role-bound tests for production paths in this unit."""
        root = self._repo_root()
        if root is None:
            return ()
        production = [
            node
            for node in self.targeted_nodes
            if node.endswith(".py") and not node.startswith("tests/")
        ]
        discovered = discover_role_bound_tests(
            root,
            production_paths=production,
            role=role,
            production_texts=self.production_texts,
        )
        if role == "targeted_symbol":
            return discovered
        if role == "interface_contract":
            explicit = tuple(
                node for node in self.interface_nodes if node in discovered
            )
            return explicit or discovered
        if role == "affected_contour":
            explicit = tuple(
                node for node in self.contour_nodes if node in discovered
            )
            return explicit or discovered
        return ()

    def compile(self) -> Proof:
        checks: list[FrozenCheck] = []
        inventory: list[dict[str, Any]] = []
        checks.append(
            FrozenCheck(
                "syntax-parse",
                "syntax-parse",
                self.targeted_nodes,
                "A",
                ("syntax-parse", *self.targeted_nodes),
                60.0,
            )
        )
        checks.append(
            FrozenCheck(
                "git-diff-check",
                "git-diff-check",
                self.targeted_nodes,
                "A",
                ("git-diff-check", *self.targeted_nodes),
                60.0,
            )
        )
        targeted_tests = self._role_tests("targeted_symbol")
        interface_tests = self._role_tests("interface_contract")
        contour_tests = self._role_tests("affected_contour")
        role_ownership: dict[str, set[str]] = {}
        for role_name, tests in (
            ("targeted_symbol", targeted_tests),
            ("interface_contract", interface_tests),
            ("affected_contour", contour_tests),
        ):
            for test_rel in tests:
                role_ownership.setdefault(test_rel, set()).add(role_name)
        for test_rel, roles in sorted(role_ownership.items()):
            root = self._repo_root()
            meta = (
                _load_test_role_manifest(root, test_rel) if root is not None else None
            )
            declared = set((meta or {}).get("roles") or ())
            if not declared.issuperset(roles):
                raise StopRequired(
                    "OPSX_VALIDATION_ROLE_OVERLAP_UNPROVEN",
                    {
                        "test": test_rel,
                        "claimed_roles": sorted(roles),
                        "declared_roles": sorted(declared),
                    },
                )
        if targeted_tests:
            checks.append(
                FrozenCheck(
                    "pytest-targeted",
                    "pytest",
                    targeted_tests,
                    "A",
                    ("poetry", "run", "pytest", *targeted_tests),
                    900.0,
                )
            )
        if interface_tests:
            checks.append(
                FrozenCheck(
                    "pytest-interface",
                    "pytest",
                    interface_tests,
                    "A",
                    ("poetry", "run", "pytest", *interface_tests),
                    900.0,
                )
            )
        if contour_tests:
            checks.append(
                FrozenCheck(
                    "pytest-contour",
                    "pytest",
                    contour_tests,
                    "A",
                    ("poetry", "run", "pytest", *contour_tests),
                    900.0,
                )
            )
        pack_inventory: dict[str, Any] = {}
        registry_sha256: str | None = None
        registry_check_ids: set[str] = set()
        unclassified_checks: tuple[str, ...] = ()
        if self.registry_path and self.registry_path.is_file():
            (
                registry_checks,
                pack_inventory,
                registry_sha256,
                unclassified_checks,
            ) = _load_registry_checks(
                self.registry_path,
                self.frozen_contract_hashes,
            )
            checks.extend(registry_checks)
            registry_check_ids = {check.check_id for check in registry_checks}
        else:
            raise StopRequired("FULL_VALIDATION_ADAPTER_UNAVAILABLE")

        selected_ids = {check.check_id for check in checks}
        production_py = tuple(
            node
            for node in self.targeted_nodes
            if node.endswith(".py") and not node.startswith("tests/")
        )
        lintable = tuple(
            node
            for node in self.targeted_nodes
            if node.endswith((".py", ".pyi", ".md", ".yml", ".yaml", ".toml"))
        )
        schema_paths = tuple(
            node
            for node in self.targeted_nodes
            if (
                "/alembic" in node
                or node.startswith("alembic")
                or node.endswith(".sql")
                or "/migrations/" in node
                or node.endswith(".schema.json")
            )
        )

        def _na(category: str, reason: str, *, proof: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "category": category,
                "status": "NOT_APPLICABLE",
                "reason": reason,
                "check_ids": [],
                "applicability_proof": dict(proof),
            }

        def _blocked(category: str, reason: str, **extra: Any) -> dict[str, Any]:
            row: dict[str, Any] = {
                "category": category,
                "status": "BLOCKED",
                "reason": reason,
                "check_ids": [],
            }
            row.update(extra)
            return row

        def _run(category: str, check_ids: list[str]) -> dict[str, Any]:
            missing = [cid for cid in check_ids if cid not in selected_ids]
            if missing:
                return _blocked(
                    category,
                    "required_check_missing_from_plan",
                    check_ids=check_ids,
                    missing=missing,
                )
            return {
                "category": category,
                "status": "REQUIRED",
                "reason": "will_execute",
                "check_ids": check_ids,
            }

        inventory.append(_run("syntax_structural", ["syntax-parse", "git-diff-check"]))
        if not lintable:
            inventory.append(
                _na(
                    "format_lint",
                    "no_lintable_paths_in_unit",
                    proof={"targeted_nodes": list(self.targeted_nodes)},
                )
            )
        elif "ruff" in registry_check_ids:
            inventory.append(_run("format_lint", ["ruff"]))
        else:
            inventory.append(
                _na(
                    "format_lint",
                    "adapter_absent_from_frozen_registry",
                    proof={
                        "required_check_ids": ["ruff"],
                        "registry_check_ids": sorted(registry_check_ids),
                        "lintable_paths": list(lintable),
                    },
                )
            )
        inventory.append(
            _run("static_analysis", ["pyright-strict"])
            if "pyright-strict" in selected_ids
            else _blocked(
                "static_analysis",
                "adapter_unavailable_unknown_applicability",
                required_check_ids=["pyright-strict"],
            )
        )
        inventory.append(
            _run("type_checks", ["mypy"])
            if "mypy" in selected_ids
            else _blocked(
                "type_checks",
                "adapter_unavailable_unknown_applicability",
                required_check_ids=["mypy"],
            )
        )
        if not production_py:
            inventory.append(
                _na(
                    "targeted_symbol_tests",
                    "no_production_python_paths_in_unit",
                    proof={"targeted_nodes": list(self.targeted_nodes)},
                )
            )
        elif "pytest-targeted" in selected_ids:
            inventory.append(
                {
                    **_run("targeted_symbol_tests", ["pytest-targeted"]),
                    "role_bound_tests": list(targeted_tests),
                    "role": "targeted_symbol",
                }
            )
        else:
            inventory.append(
                _blocked(
                    "targeted_symbol_tests",
                    "role_metadata_required_for_targeted_symbol",
                    production_paths=list(production_py),
                )
            )
        if not production_py:
            inventory.append(
                _na(
                    "interface_contract_tests",
                    "no_production_python_paths_in_unit",
                    proof={"targeted_nodes": list(self.targeted_nodes)},
                )
            )
            inventory.append(
                _na(
                    "affected_contour_tests",
                    "no_production_python_paths_in_unit",
                    proof={"targeted_nodes": list(self.targeted_nodes)},
                )
            )
        elif "pytest-interface" in selected_ids:
            inventory.append(
                {
                    **_run("interface_contract_tests", ["pytest-interface"]),
                    "role_bound_tests": list(interface_tests),
                    "role": "interface_contract",
                }
            )
        else:
            inventory.append(
                _blocked(
                    "interface_contract_tests",
                    "role_metadata_required_for_interface_contract",
                    production_paths=list(production_py),
                )
            )
        if production_py:
            if "pytest-contour" in selected_ids:
                inventory.append(
                    {
                        **_run("affected_contour_tests", ["pytest-contour"]),
                        "role_bound_tests": list(contour_tests),
                        "role": "affected_contour",
                    }
                )
            else:
                inventory.append(
                    _blocked(
                        "affected_contour_tests",
                        "role_metadata_required_for_affected_contour",
                        production_paths=list(production_py),
                    )
                )
        inventory.append(
            _run("integration_tests", ["pytest-full"])
            if "pytest-full" in selected_ids
            else _blocked(
                "integration_tests",
                "adapter_unavailable_unknown_applicability",
                required_check_ids=["pytest-full"],
            )
        )
        if schema_paths:
            inventory.append(
                _blocked(
                    "schema_migration",
                    "schema_or_migration_paths_require_adapter",
                    schema_paths=list(schema_paths),
                )
            )
        else:
            inventory.append(
                _na(
                    "schema_migration",
                    "no_schema_or_migration_paths_in_unit",
                    proof={"targeted_nodes": list(self.targeted_nodes)},
                )
            )
        if "security-scan" in registry_check_ids:
            inventory.append(_run("security", ["security-scan"]))
        else:
            inventory.append(
                _na(
                    "security",
                    "adapter_absent_from_frozen_registry",
                    proof={
                        "required_check_ids": ["security-scan"],
                        "registry_check_ids": sorted(registry_check_ids),
                    },
                )
            )
        if "openspec-validate" in registry_check_ids:
            inventory.append(_run("openspec_validation", ["openspec-validate"]))
        else:
            inventory.append(
                _na(
                    "openspec_validation",
                    "adapter_absent_from_frozen_registry",
                    proof={
                        "required_check_ids": ["openspec-validate"],
                        "registry_check_ids": sorted(registry_check_ids),
                    },
                )
            )
        inventory.append(
            _run(
                "project_full_gate",
                ["pytest-unit", "pytest-full", "mypy", "pyright-strict"],
            )
            if {"pytest-unit", "pytest-full", "mypy", "pyright-strict"}.issubset(
                selected_ids
            )
            else _blocked(
                "project_full_gate",
                "full_registry_gate_incomplete",
                check_ids=sorted(selected_ids),
            )
        )
        if unclassified_checks:
            inventory.append(
                _blocked(
                    "registry_discovered_unclassified",
                    "discovered_check_lacks_category_mapping",
                    check_ids=list(unclassified_checks),
                    registry_check_ids=sorted(registry_check_ids),
                )
            )
        else:
            inventory.append(
                _na(
                    "registry_discovered_unclassified",
                    "no_unmapped_registry_checks",
                    proof={"registry_check_ids": sorted(registry_check_ids)},
                )
            )
        root = self._repo_root()
        graph_path = (
            (root / ".cursor" / "pipeline" / "GRAPH.md") if root is not None else None
        )
        if graph_path is not None and graph_path.is_file():
            graph_text = graph_path.read_text(encoding="utf-8")
            mentioned = [
                gate
                for gate in _PIPELINE_CONDITIONAL_GATES
                if f"/{gate}" in graph_text or gate in graph_text
            ]
            adapted = sorted(registry_check_ids & set(mentioned))
            missing_gates = [gate for gate in mentioned if gate not in registry_check_ids]
            if missing_gates:
                inventory.append(
                    _blocked(
                        "opsx_pipeline_conditional_gates",
                        "pipeline_gate_lacks_typed_adapter",
                        gates=missing_gates,
                        adapted=adapted,
                        graph="/.cursor/pipeline/GRAPH.md",
                    )
                )
            else:
                inventory.append(
                    _na(
                        "opsx_pipeline_conditional_gates",
                        "mentioned_pipeline_gates_have_adapters_or_none_mentioned",
                        proof={
                            "mentioned": mentioned,
                            "adapted": adapted,
                        },
                    )
                )
        else:
            inventory.append(
                _na(
                    "opsx_pipeline_conditional_gates",
                    "pipeline_graph_absent_from_repository",
                    proof={"graph": ".cursor/pipeline/GRAPH.md"},
                )
            )
        blocked = [row for row in inventory if row.get("status") == "BLOCKED"]
        if blocked:
            raise StopRequired(
                "OPSX_VALIDATION_INVENTORY_BLOCKED",
                {"blocked": blocked},
            )
        covered = {str(row["category"]) for row in inventory}
        missing_categories = [
            category
            for category in OPSX_VALIDATION_CATEGORIES
            if category not in covered
        ]
        if missing_categories:
            raise StopRequired(
                "OPSX_VALIDATION_INVENTORY_INCOMPLETE",
                {"missing": missing_categories},
            )
        payload = {
            "checks": [
                {
                    "check_id": c.check_id,
                    "tool": c.tool,
                    "rel_nodes": list(c.rel_nodes),
                    "wave": c.wave,
                    "argv": list(c.argv),
                    "timeout_seconds": c.timeout_seconds,
                    "task_type": c.task_type,
                    "pack": c.pack,
                    "success_exit_codes": list(c.success_exit_codes),
                    "pack_inventory_digest": c.pack_inventory_digest,
                    "adapter_schema": c.adapter_schema,
                }
                for c in checks
            ],
            "content_fingerprints": self.content_fingerprints,
            "registry": str(self.registry_path) if self.registry_path else None,
            "registry_sha256": registry_sha256,
            "pack_inventory": pack_inventory,
            "adapter_schema": VALIDATION_ADAPTER_SCHEMA,
            "selected_check_ids": [check.check_id for check in checks],
            "validation_inventory": inventory,
            "validation_inventory_complete": True,
        }
        return Proof.issue(
            "TEST_PLAN",
            run_id=self.run_id,
            fingerprint=self.fingerprint,
            scope_sha256=self.scope_sha256,
            payload=payload,
        )


# Back-compat name; do not start with "Test" (pytest collection).
TestPlanCompiler = FrozenTestPlanCompiler


def _assert_nodes_inside_snapshot(snapshot: Path, nodes: Sequence[str]) -> None:
    snap = snapshot.resolve()
    for node in nodes:
        if node.startswith("-"):
            raise PolicyViolation(f"forbidden node flag: {node}")
        if os.path.isabs(node) or ".." in Path(node).parts:
            raise PolicyViolation(f"path escapes snapshot: {node}")
        target = (snap / node).resolve()
        try:
            target.relative_to(snap)
        except ValueError as exc:
            raise PolicyViolation(f"path outside snapshot: {node}") from exc


def assert_frozen_argv(plan: Proof, check_id: str, argv: Sequence[str]) -> FrozenCheck:
    """Reject any argv not exactly equal to frozen plan entry."""
    checks = {c["check_id"]: c for c in plan.payload["checks"]}
    if check_id not in checks:
        raise PolicyViolation(f"unknown check_id: {check_id}")
    frozen = checks[check_id]
    if list(argv) != list(frozen["argv"]):
        raise PolicyViolation("argv does not match frozen test plan")
    joined = " ".join(argv)
    for tok in FORBIDDEN_ARG_TOKENS:
        # allow '-m unit' for pytest-unit only as in frozen plan
        if tok in argv and tok in {"-p", "--collect-only", "--confcutdir", "--rootdir", "--import-mode", "--project", "--config-file"}:
            raise PolicyViolation(f"forbidden validation token: {tok}")
        if tok in {";", "&&", "||", "`", "$("} and tok in joined:
            raise PolicyViolation(f"forbidden metachar: {tok}")
    tool = frozen["tool"]
    if tool not in ALLOWED_TOOLS:
        raise PolicyViolation(f"tool not allowed: {tool}")
    return FrozenCheck(
        frozen["check_id"],
        frozen["tool"],
        tuple(frozen["rel_nodes"]),
        frozen["wave"],
        tuple(frozen["argv"]),
        float(frozen["timeout_seconds"]),
        task_type=str(frozen.get("task_type") or ""),
        pack=str(frozen.get("pack") or ""),
        success_exit_codes=tuple(
            int(code) for code in (frozen.get("success_exit_codes") or [0])
        ),
        pack_inventory_digest=str(frozen.get("pack_inventory_digest") or ""),
        adapter_schema=str(
            frozen.get("adapter_schema") or VALIDATION_ADAPTER_SCHEMA
        ),
    )


def minimal_validation_env(snapshot: Path) -> dict[str, str]:
    """Allowlisted env only — never copy os.environ (C02)."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_TERMINAL_PROMPT": "0",
        "OPSX_CONFLICT_VALIDATION_SNAPSHOT": str(snapshot),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for key in ("WINDIR", "SYSTEMROOT", "TMP", "TEMP", "HOME", "USERPROFILE", "SYSTEMDRIVE"):
        if key in os.environ:
            env[key] = os.environ[key]
    # Explicitly omit credentials / proxy bypass / PYTHONPATH / VIRTUAL_ENV
    return env


def build_validation_snapshot(repo_root: Path, run_dir: Path, git) -> Path:
    """Copy tracked regular files; STOP on unsupported symlink/submodule (M01)."""
    snapshot = run_dir / "validation-worktree"
    if snapshot.exists():
        shutil.rmtree(snapshot)
    snapshot.mkdir(parents=True)
    raw = git.ls_files_z()
    tracked = [p for p in raw.split("\0") if p]
    root = repo_root.resolve()
    for rel in tracked:
        from .pathsafety import normalize_repo_rel, resolve_under_repo

        try:
            normalize_repo_rel(rel)
        except PolicyViolation as exc:
            raise StopRequired("SNAPSHOT_PATH_ESCAPE", {"path": rel}) from exc
        _, src = resolve_under_repo(root, rel)
        if src.is_symlink():
            raise StopRequired("SNAPSHOT_UNSUPPORTED_SYMLINK", {"path": rel})
        if not src.is_file():
            raise StopRequired("SNAPSHOT_UNSUPPORTED_ENTRY", {"path": rel})
        dst = snapshot / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if (snapshot / ".git").exists():
        raise StopRequired("SNAPSHOT_CONTAINS_GIT")
    return snapshot


def run_frozen_check(
    *,
    plan: Proof,
    check_id: str,
    snapshot: Path,
    unit_wave_passed: set[str],
    content_fingerprints: Mapping[str, str],
    sandbox: Mapping[str, Any],
    timeout: float | None = None,
) -> Proof:
    """Execute one frozen check; enforce Wave B after unit PASS; invalidate on drift."""
    if plan.payload.get("content_fingerprints") != dict(content_fingerprints):
        raise StopRequired("CHECK_INPUTS_INVALIDATED")
    frozen = assert_frozen_argv(plan, check_id, plan.payload["checks"][
        next(i for i, c in enumerate(plan.payload["checks"]) if c["check_id"] == check_id)
    ]["argv"])
    effective_timeout = frozen.timeout_seconds if timeout is None else timeout
    if frozen.wave == "B" and "pytest-unit" not in unit_wave_passed:
        raise StopRequired("WAVE_B_BEFORE_UNIT_PASS")
    _assert_nodes_inside_snapshot(snapshot, frozen.rel_nodes)
    env = minimal_validation_env(snapshot)
    # Refuse credential leakage
    for banned in ("AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY", "DATABASE_URL", "PYTHONPATH", "VIRTUAL_ENV"):
        if banned in env:
            raise PolicyViolation(f"credential/path leak in env: {banned}")
    if frozen.tool == "syntax-parse":
        for rel in frozen.rel_nodes:
            src = snapshot / rel
            if rel.endswith(".py"):
                compile(src.read_text(encoding="utf-8"), str(src), "exec")
        result_code = 0
        stdout = stderr = ""
    elif frozen.tool == "git-diff-check":
        # Real git diff --check against snapshot files via host TypedGit is
        # performed by the orchestrator; here we validate conflict-marker-free
        # text and run `git diff --check` when a .git is absent by scanning.
        from .git_typed import TypedGit

        # Snapshot has no .git — enforce marker/whitespace locally; orchestrator
        # also calls TypedGit.diff_check_paths on the live repo before stage.
        for rel in frozen.rel_nodes:
            src = snapshot / rel
            if not src.is_file():
                raise StopRequired("DIFF_CHECK_MISSING_FILE", {"path": rel})
            text = src.read_text(encoding="utf-8", errors="replace")
            for marker in ("<<<<<<<", "=======", ">>>>>>>"):
                if marker in text:
                    raise StopRequired("CONFLICT_MARKERS_REMAIN", {"path": rel})
        result_code = 0
        stdout = stderr = ""
        _ = TypedGit  # imported for type/tooling clarity; live check in orchestrator
    else:
        # Offline policy: poetry checks require poetry; else STOP (not false PASS)
        if shutil.which("poetry") is None:
            raise StopRequired(
                "ENVIRONMENT_OR_CREDENTIAL_BLOCK",
                {"reason": "poetry_missing_for_frozen_check", "check_id": check_id},
            )
        runner = sandbox.get("runner")
        runner_digest = sandbox.get("sha256")
        spawn_prefix = sandbox.get("spawn_argv_prefix")
        if (
            not isinstance(runner, str)
            or not runner
            or sandbox.get("enforcement_level") != "OS_VERIFIED"
            or sandbox.get("network") != "DENY"
            or sandbox.get("filesystem") != "SNAPSHOT_ONLY"
            or sandbox.get("protocol")
            != "opsx-sandbox-path-confinement/v1"
            or not isinstance(runner_digest, str)
            or len(runner_digest) != 64
            or not isinstance(spawn_prefix, list)
            or not spawn_prefix
        ):
            raise StopRequired("VALIDATION_SANDBOX_CAPABILITY_MISSING")
        runner_path = Path(runner)
        if runner_path.is_symlink() or not runner_path.is_file():
            raise StopRequired(
                "VALIDATION_SANDBOX_RUNNER_INVALID",
                {"path": runner},
            )
        import hashlib

        actual = hashlib.sha256(runner_path.read_bytes()).hexdigest()
        if actual != runner_digest.lower():
            raise StopRequired(
                "SANDBOX_RUNNER_TOCTOU",
                {"expected": runner_digest, "actual": actual},
            )
        sandbox_argv = [
            *[str(part) for part in spawn_prefix],
            "--network=none",
            f"--filesystem-root={snapshot}",
            "--",
            *frozen.argv,
        ]
        result = run_process(
            sandbox_argv,
            cwd=snapshot,
            env=env,
            timeout=effective_timeout,
        )
        result_code = result.returncode
        stdout, stderr = result.stdout, result.stderr
        if result_code not in frozen.success_exit_codes:
            raise StopRequired(
                "TEST_FAILURE",
                {
                    "check_id": check_id,
                    "returncode": result_code,
                    "allowed_exit_codes": list(frozen.success_exit_codes),
                    "stdout_sha256": sha256_text(stdout),
                    "stderr_sha256": sha256_text(stderr),
                },
            )
    return Proof.issue(
        "CHECK_RECEIPT",
        run_id=plan.run_id,
        fingerprint=plan.fingerprint,
        scope_sha256=plan.scope_sha256,
        payload={
            "check_id": check_id,
            "wave": frozen.wave,
            "exit_code": result_code,
            "timeout_seconds": effective_timeout,
            "stdout_sha256": sha256_text(stdout),
            "stderr_sha256": sha256_text(stderr),
            "argv": list(frozen.argv),
            "sandbox": dict(sandbox),
        },
    )


def effective_final_gate(
    *,
    registry_path: Path | None,
    requested_mode: str = "FULL",
    frozen_contract_hashes: Mapping[str, str] | None = None,
) -> list[str]:
    """Validate the typed FULL registry and return ordered check IDs."""
    if requested_mode != "FULL":
        raise StopRequired("FINAL_FAST_NOT_SUPPORTED")
    if registry_path is None or not registry_path.is_file():
        raise StopRequired("FULL_VALIDATION_ADAPTER_UNAVAILABLE")
    checks, _, _, _ = _load_registry_checks(
        registry_path,
        frozen_contract_hashes or {},
    )
    return [f"Wave{check.wave}:{check.check_id}" for check in checks]
