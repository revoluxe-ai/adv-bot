"""FINAL_ACCEPTANCE control plane миграций ClickHouse.

Spec ``clickhouse-migration-lifecycle``, задача 15. Проверяется runner surface,
замыкание всех 42 scenario на именованные тесты и отсутствие forbidden imports.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_PACKAGE = _REPO / "scripts" / "clickhouse_migration_control_plane"
_SPEC = (
    _REPO
    / "openspec"
    / "changes"
    / "clickhouse-migrations-control-plane"
    / "specs"
    / "clickhouse-migration-lifecycle"
    / "spec.md"
)
_DECISION = (
    _REPO
    / "openspec"
    / "changes"
    / "clickhouse-migrations-control-plane"
    / "decisions"
    / "clickhouse-migration-lifecycle-ownership"
    / "decision.md"
)


def test_runner_help_lists_the_documented_commands() -> None:
    """Final acceptance: documented ``python -m ... --help`` работает."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.clickhouse_migration_control_plane",
            "--help",
        ],
        cwd=_REPO,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    for command in (
        "status",
        "validate",
        "plan",
        "inspect",
        "ensure-ledger",
        "reconcile",
        "apply",
    ):
        assert command in completed.stdout


def test_runner_validate_is_read_only_and_reports_success() -> None:
    """Scenario: Honest success and refusal — intact validate имеет exit 0."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.clickhouse_migration_control_plane",
            "validate",
        ],
        cwd=_REPO,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert '"code": "ok"' in completed.stdout
    assert '"success": true' in completed.stdout


def test_every_planned_scenario_is_named_by_a_target_test() -> None:
    """Final acceptance: каждый из 42 scenario spec привязан к test function."""
    scenario_names: list[str] = []
    for line in _SPEC.read_text(encoding="utf-8").splitlines():
        prefix = "#### Scenario: "
        if line.startswith(prefix):
            scenario_names.append(line[len(prefix) :].strip())

    test_docstrings: list[str] = []
    for path in sorted(
        (_REPO / "tests" / "unit").glob("test_clickhouse_migration_*.py")
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            docstring = ast.get_docstring(node) or ""
            test_docstrings.append(" ".join(docstring.split()))

    assert len(scenario_names) == 42
    missing = [
        name
        for name in scenario_names
        if not any(" ".join(name.split()) in doc for doc in test_docstrings)
    ]
    assert missing == []


def test_control_plane_import_graph_excludes_forbidden_runtime_adapters() -> None:
    """Scenarios: The application client is not the migration executor; Alembic stays out of ClickHouse migrations."""
    imported: set[str] = set()
    for path in sorted(_PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)

    assert not any(name.startswith("app.utils.click_house") for name in imported)
    assert not any(name.startswith("app.db.migrate") for name in imported)
    assert not any(name.startswith("alembic") for name in imported)
    assert not any(
        name.startswith("tests.support.rewrite_default_db_ch_client")
        for name in imported
    )


def test_proposed_decision_stays_proposed_and_shop_wide_runtime_is_outside_package() -> None:
    """Scenarios: Shop-wide expansion waits; proposed lifecycle decision не промотирован."""
    decision = _DECISION.read_text(encoding="utf-8")
    package_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(_PACKAGE.glob("*.py"))
    )

    assert "Proposed" in decision
    assert "shop_runner" not in package_text
    assert "CampaignCollectionRouteResolver" not in package_text
