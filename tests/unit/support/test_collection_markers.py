"""Unit: marker collection — destructive_local не в fast/integration."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.unit
def test_live_pg_files_are_under_integration_path() -> None:
    """Live PG suites живут в tests/integration/, не в tests/unit/."""
    root = Path(__file__).resolve().parents[2]
    live_files = [
        root
        / "integration"
        / "card_ab_hold"
        / "test_concurrent_generation_live_pg.py",
        root / "integration" / "card_ab_hold" / "test_migration_epoch_live_pg.py",
        root / "integration" / "test_ab_hold_pg_writers_live.py",
    ]
    for path in live_files:
        assert path.is_file(), path
        assert "/tests/unit/" not in str(path).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        assert "@pytest.mark.destructive_local" in text
        assert "@pytest.mark.integration" not in text
        assert "@pytest.mark.fast" not in text


@pytest.mark.unit
def test_collection_modifyitems_skips_fast_for_integration_marker() -> None:
    """Explicit @pytest.mark.integration не получает auto-fast даже под tests/unit/."""
    root_conftest_path = Path(__file__).resolve().parents[3] / "conftest.py"
    src = root_conftest_path.read_text(encoding="utf-8")
    assert "destructive_local" in src
    assert "not has_destructive" in src or "has_destructive" in src
    assert "pytest.mark.fast" in src

    def _modify(items: list[object]) -> None:
        for item in items:
            path = str(item.fspath).replace("\\", "/")  # type: ignore[attr-defined]
            is_unit_path = "/tests/unit/" in path or path.endswith("/tests/unit")
            has_integration = item.get_closest_marker("integration") is not None  # type: ignore[attr-defined]
            has_destructive = item.get_closest_marker("destructive_local") is not None  # type: ignore[attr-defined]
            if (
                is_unit_path
                and not has_integration
                and not has_destructive
                and item.get_closest_marker("fast") is None  # type: ignore[attr-defined]
            ):
                item.add_marker(SimpleNamespace(mark=SimpleNamespace(name="fast")))  # type: ignore[attr-defined]

    class _Node:
        def __init__(self, path: str, markers: set[str]) -> None:
            self.fspath = path
            self._markers = set(markers)
            self.added: list[object] = []

        def get_closest_marker(self, name: str):  # noqa: ANN201
            return object() if name in self._markers else None

        def add_marker(self, marker: object) -> None:
            self.added.append(marker)

    item = _Node("/repo/tests/unit/fake/test_live.py", {"integration"})
    _modify([item])
    fast_added = any(
        getattr(getattr(m, "mark", m), "name", None) == "fast" for m in item.added
    )
    assert not fast_added

    destructive = _Node(
        "/repo/tests/integration/fake/test_live_pg.py", {"destructive_local"}
    )
    _modify([destructive])
    assert not any(
        getattr(getattr(m, "mark", m), "name", None) == "fast"
        for m in destructive.added
    )

    unit_only = _Node("/repo/tests/unit/fake/test_unit.py", set())
    _modify([unit_only])
    assert any(
        getattr(getattr(m, "mark", m), "name", None) == "fast" for m in unit_only.added
    )


@pytest.mark.unit
def test_allowed_ch_database_is_dedicated() -> None:
    from tests.support.destructive_clickhouse import ALLOWED_CH_DATABASE

    assert ALLOWED_CH_DATABASE == "test_adv_bot_clickhouse"
    assert ALLOWED_CH_DATABASE != "default_db"


def _source_segment(src: str, node: ast.AST) -> str:
    """Безопасно извлечь исходник узла AST."""
    return ast.get_source_segment(src, node) or ""


def _iter_test_files(root: Path) -> list[Path]:
    """Вернуть python test-файлы согласно pytest-шаблонам проекта."""
    files = []
    for path in root.rglob("*.py"):
        name = path.name
        if name.startswith("test_") or name.endswith("_test.py") or name == "tests.py":
            files.append(path)
    return files


def _decorators_have_mark(src: str, node: ast.AST, mark_name: str) -> bool:
    """Проверить наличие ``@pytest.mark.<mark_name>`` в decorators."""
    decorators = getattr(node, "decorator_list", [])
    token = f"pytest.mark.{mark_name}"
    return any(token in _source_segment(src, dec) for dec in decorators)


@pytest.mark.unit
def test_no_duplicate_pytestmark_assignment_in_test_modules() -> None:
    """Запретить повторное ``pytestmark = ...`` (защита от marker overwrite)."""
    tests_root = Path(__file__).resolve().parents[2]
    offenders: list[str] = []

    for path in _iter_test_files(tests_root):
        src = path.read_text(encoding="utf-8-sig")
        # Без двух вхождений pytestmark повторного assignment быть не может.
        if src.count("pytestmark") < 2:
            continue
        tree = ast.parse(src)
        assignments = 0
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "pytestmark"
                for target in node.targets
            ):
                assignments += 1
        if assignments > 1:
            offenders.append(f"{path.relative_to(tests_root.parent).as_posix()} ({assignments})")

    assert not offenders, (
        "Repeated pytestmark assignments detected:\n- "
        + "\n- ".join(offenders)
    )


@pytest.mark.unit
def test_destructive_fixture_callers_have_effective_marker() -> None:
    """Callers risky fixtures must have effective ``destructive_local`` marker.

    Дополнительно запрещает module-level destructive scope, который помечает
    тесты без risky fixture dependency.
    """
    tests_root = Path(__file__).resolve().parents[2]
    risky_fixtures = {
        "async_session",
        "postgres_session",
        "setup_test_database",
        "clickhouse_client",
    }

    missing_marker: list[str] = []
    leaked_module_scope: list[str] = []

    for path in _iter_test_files(tests_root):
        src = path.read_text(encoding="utf-8-sig")
        # Fast-path: без risky fixture и без destructive_local AST не нужен —
        # файл не может дать missing_marker / leaked_module_scope.
        if "destructive_local" not in src and not any(
            name in src for name in risky_fixtures
        ):
            continue
        tree = ast.parse(src)

        module_mark_assignments: list[ast.Assign] = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "pytestmark"
                for target in node.targets
            ):
                module_mark_assignments.append(node)
        module_has_destructive = False
        if module_mark_assignments:
            module_has_destructive = "pytest.mark.destructive_local" in _source_segment(
                src, module_mark_assignments[-1]
            )

        # Собираем локальные fixture -> deps для транзитивного анализа.
        fixture_deps: dict[str, list[str]] = {}
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any("pytest.fixture" in _source_segment(src, d) for d in node.decorator_list):
                continue
            fixture_name = node.name
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and "pytest.fixture" in _source_segment(
                    src, decorator.func
                ):
                    for kw in decorator.keywords:
                        if (
                            kw.arg == "name"
                            and isinstance(kw.value, ast.Constant)
                            and isinstance(kw.value.value, str)
                        ):
                            fixture_name = kw.value.value
            fixture_deps[fixture_name] = [arg.arg for arg in node.args.args if arg.arg != "self"]

        def depends_on_risky(initial_params: list[str]) -> bool:
            stack = [p for p in initial_params if p != "self"]
            seen: set[str] = set()
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                if current in risky_fixtures:
                    return True
                stack.extend(fixture_deps.get(current, []))
            return False

        class_marks: dict[str, bool] = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_marks[node.name] = _decorators_have_mark(
                    src, node, "destructive_local"
                )

        def check_test_node(
            node: ast.FunctionDef | ast.AsyncFunctionDef, *, class_name: str | None = None
        ) -> None:
            if not node.name.startswith("test_"):
                return
            params = [arg.arg for arg in node.args.args]
            uses_risky = depends_on_risky(params)
            fn_has_destructive = _decorators_have_mark(src, node, "destructive_local")
            class_has_destructive = class_marks.get(class_name or "", False)
            effective_destructive = (
                fn_has_destructive or class_has_destructive or module_has_destructive
            )

            rel = path.relative_to(tests_root.parent).as_posix()
            label = f"{rel}::{node.name}"
            if uses_risky and not effective_destructive:
                missing_marker.append(label)
            if (
                module_has_destructive
                and not class_has_destructive
                and not fn_has_destructive
                and not uses_risky
            ):
                leaked_module_scope.append(label)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                check_test_node(node)
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        check_test_node(item, class_name=node.name)

    assert not missing_marker, (
        "Risky fixture callers without effective destructive_local marker:\n- "
        + "\n- ".join(missing_marker)
    )
    assert not leaked_module_scope, (
        "Module-level destructive_local leaked onto non-risky tests:\n- "
        + "\n- ".join(leaked_module_scope)
    )
