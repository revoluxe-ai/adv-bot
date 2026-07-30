"""Статическая safety-проверка цепочки Alembic-миграций vs ``stage``.

Тест сам находит все revision-файлы в диффе от ``origin/stage``/``stage``
(включая uncommitted) и в ``upgrade()`` ищет опасные команды:

- destructive Alembic ops: drop_*/alter_column/rename_*/batch_alter_table/execute
- опасные SQL-литералы: DROP/ALTER COLUMN/TRUNCATE/RENAME/...

Дополнительно: ``nullable=False`` add_column требует ``server_default``.

Исторические миграции, уже лежащие на stage, не сканируются — они уже
применены и не входят в deploy-цепочку этого диффа.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_VERSIONS = _REPO_ROOT / "alembic_" / "versions"

_FORBIDDEN_UPGRADE_OPS: frozenset[str] = frozenset(
    {
        "drop_column",
        "drop_table",
        "drop_constraint",
        "drop_index",
        "alter_column",
        "rename_table",
        "rename_column",
        "batch_alter_table",
        "execute",
    }
)

# SQL-фрагменты, которые в upgrade делают миграцию online-unsafe.
_DANGEROUS_SQL_RE = re.compile(
    r"\b("
    r"DROP\s+TABLE|DROP\s+COLUMN|DROP\s+INDEX|DROP\s+CONSTRAINT|"
    r"TRUNCATE|"
    r"ALTER\s+TABLE\s+\S+\s+ALTER\s+COLUMN|"
    r"ALTER\s+COLUMN|"
    r"RENAME\s+TO|RENAME\s+COLUMN|"
    r"SET\s+NOT\s+NULL|"
    r"TYPE\s+\w+\s+USING"  # column type rewrite
    r")\b",
    re.IGNORECASE,
)


def _git_output(*args: str) -> str:
    """Запуск git в корне репо; пустая строка при отсутствии ref/ошибке."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _stage_merge_base() -> str | None:
    """merge-base HEAD с origin/stage или stage."""
    for ref in ("origin/stage", "stage"):
        base = _git_output("merge-base", "HEAD", ref).strip()
        if base:
            return base
    return None


def _version_paths_from_git_names(names: list[str]) -> list[Path]:
    out: list[Path] = []
    for name in names:
        norm = name.replace("\\", "/").strip()
        if not norm.startswith("alembic_/versions/") or not norm.endswith(".py"):
            continue
        path = _REPO_ROOT / Path(*norm.split("/"))
        if path.is_file() and path.name != "__init__.py":
            out.append(path)
    return out


def discover_stage_diff_migration_chain() -> list[Path]:
    """Цепочка migration-файлов, которых нет на stage (diff + worktree).

    Returns:
        Отсортированный список уникальных Path в ``alembic_/versions``.
    """
    base = _stage_merge_base()
    names: set[str] = set()
    if base:
        # committed diff vs merge-base
        for line in _git_output(
            "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", "alembic_/versions"
        ).splitlines():
            if line.strip():
                names.add(line.strip())
        # unstaged + staged vs merge-base (ловит ещё не закоммиченные ревизии)
        for line in _git_output(
            "diff", "--name-only", "--diff-filter=AM", base, "--", "alembic_/versions"
        ).splitlines():
            if line.strip():
                names.add(line.strip())
        for line in _git_output(
            "diff", "--cached", "--name-only", "--diff-filter=AM", base, "--", "alembic_/versions"
        ).splitlines():
            if line.strip():
                names.add(line.strip())
    else:
        # fallback: untracked/modified versions в индексе/worktree
        for line in _git_output(
            "ls-files", "--others", "--modified", "--exclude-standard", "--", "alembic_/versions"
        ).splitlines():
            if line.strip():
                names.add(line.strip())

    paths = sorted(set(_version_paths_from_git_names(sorted(names))), key=lambda p: p.name)
    return paths


def _upgrade_fn(tree: ast.Module) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            return node
    return None


def _op_calls_in_upgrade(upgrade: ast.FunctionDef) -> list[tuple[str, ast.Call]]:
    found: list[tuple[str, ast.Call]] = []
    for node in ast.walk(upgrade):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "op":
                found.append((func.attr, node))
    return found


def _string_literals_in(node: ast.AST) -> list[str]:
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            out.append(child.value)
        elif isinstance(child, ast.JoinedStr):
            # f-string: собираем постоянные куски
            parts: list[str] = []
            for v in child.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
            if parts:
                out.append("".join(parts))
    return out


def _kw_bool(call: ast.Call, name: str) -> bool | None:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, bool):
                return kw.value.value
    return None


def _has_server_default(call: ast.Call) -> bool:
    return any(kw.arg == "server_default" for kw in call.keywords)


def _column_name(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant):
        val = call.args[0].value
        if isinstance(val, str):
            return val
    return None


def _add_column_defs(upgrade: ast.FunctionDef) -> list[ast.Call]:
    cols: list[ast.Call] = []
    for op_name, op_call in _op_calls_in_upgrade(upgrade):
        if op_name != "add_column":
            continue
        for node in ast.walk(op_call):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "Column"
            ):
                cols.append(node)
    return cols


def scan_upgrade_dangerous_commands(path: Path) -> list[str]:
    """Находит опасные op.* и SQL в ``upgrade()`` одной миграции."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    upgrade = _upgrade_fn(tree)
    if upgrade is None:
        return [f"{path.name}: missing upgrade()"]

    findings: list[str] = []
    for op_name, _call in _op_calls_in_upgrade(upgrade):
        if op_name in _FORBIDDEN_UPGRADE_OPS:
            findings.append(f"{path.name}: dangerous op.{op_name}() in upgrade()")

    for literal in _string_literals_in(upgrade):
        match = _DANGEROUS_SQL_RE.search(literal)
        if match:
            snippet = " ".join(literal.split())[:120]
            findings.append(
                f"{path.name}: dangerous SQL in upgrade() "
                f"({match.group(1)!r}): {snippet!r}"
            )
    return findings


def scan_not_null_without_server_default(path: Path) -> list[str]:
    """NOT NULL add_column без server_default — unsafe для существующих строк."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    upgrade = _upgrade_fn(tree)
    if upgrade is None:
        return []
    findings: list[str] = []
    for col in _add_column_defs(upgrade):
        if _kw_bool(col, "nullable") is False and not _has_server_default(col):
            name = _column_name(col) or "<unknown>"
            findings.append(
                f"{path.name}: nullable=False column {name!r} without server_default"
            )
    return findings


@pytest.fixture(scope="module")
def stage_diff_migrations() -> list[Path]:
    """Цепочка migration-файлов диффа от stage; skip если цепочка пуста."""
    paths = discover_stage_diff_migration_chain()
    if not paths:
        pytest.skip(
            "no alembic_/versions changes vs stage "
            "(need origin/stage|stage and a non-empty migration diff)"
        )
    return paths


@pytest.mark.unit
def test_stage_diff_migration_chain_discovered(stage_diff_migrations: list[Path]) -> None:
    """Дифф от stage должен дать хотя бы одну migration в цепочке."""
    assert stage_diff_migrations
    for path in stage_diff_migrations:
        assert path.is_file()
        assert path.parent == _VERSIONS


@pytest.mark.unit
def test_stage_diff_migration_chain_has_no_dangerous_upgrade_commands(
    stage_diff_migrations: list[Path],
) -> None:
    """Во всей цепочке диффа от stage ``upgrade`` без опасных op/SQL."""
    all_findings: list[str] = []
    for path in stage_diff_migrations:
        all_findings.extend(scan_upgrade_dangerous_commands(path))
    assert not all_findings, (
        "dangerous commands in stage→HEAD migration chain:\n- "
        + "\n- ".join(all_findings)
    )


@pytest.mark.unit
def test_stage_diff_migration_chain_not_null_has_server_default(
    stage_diff_migrations: list[Path],
) -> None:
    """Во всей цепочке NOT NULL add_column только с server_default."""
    all_findings: list[str] = []
    for path in stage_diff_migrations:
        all_findings.extend(scan_not_null_without_server_default(path))
    assert not all_findings, (
        "NOT NULL without server_default in stage→HEAD chain:\n- "
        + "\n- ".join(all_findings)
    )
