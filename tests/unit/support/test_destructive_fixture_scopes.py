"""AST/contract tests: fixture scopes and gate-before-infra acquisition."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_CONFTEST = _ROOT / "conftest.py"


def _fixture_defs(src: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Имя fixture → AST function (учитывает name= kw)."""
    tree = ast.parse(src)
    out: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            text = ast.get_source_segment(src, dec) or ""
            if "pytest.fixture" not in text:
                continue
            name = node.name
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if (
                        kw.arg == "name"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ):
                        name = kw.value.value
            out[name] = node
            out[node.name] = node
    return out


def _fixture_scope(src: str, node: ast.AST) -> str:
    """Вернуть scope=... или function по умолчанию."""
    for dec in getattr(node, "decorator_list", []):
        text = ast.get_source_segment(src, dec) or ""
        if "pytest.fixture" not in text:
            continue
        if isinstance(dec, ast.Call):
            for kw in dec.keywords:
                if kw.arg == "scope" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
        if "scope=" in text:
            # fallback parse
            if 'scope="session"' in text or "scope='session'" in text:
                return "session"
            if 'scope="function"' in text or "scope='function'" in text:
                return "function"
    return "function"


@pytest.mark.unit
def test_compose_owner_is_session_scoped() -> None:
    """``_test_infra_lifecycle`` — session owner Compose/schema."""
    src = _CONFTEST.read_text(encoding="utf-8")
    fixtures = _fixture_defs(src)
    assert "_test_infra_lifecycle" in fixtures
    assert _fixture_scope(src, fixtures["_test_infra_lifecycle"]) == "session"
    body = ast.get_source_segment(src, fixtures["_test_infra_lifecycle"]) or ""
    assert "teardown" in body
    assert "yield" in body


@pytest.mark.unit
def test_data_reset_is_function_scoped() -> None:
    """PG data reset — function; не session schema bootstrap."""
    src = _CONFTEST.read_text(encoding="utf-8")
    fixtures = _fixture_defs(src)
    assert "reset_postgres_test_data" in fixtures
    assert _fixture_scope(src, fixtures["reset_postgres_test_data"]) == "function"
    assert _fixture_scope(src, fixtures["async_engine"]) == "function"
    assert _fixture_scope(src, fixtures["clickhouse_client"]) == "function"
    assert _fixture_scope(src, fixtures["setup_test_database"]) == "function"


@pytest.mark.unit
def test_no_autouse_clean_db() -> None:
    """Широкий autouse clean_db удалён — reset только через PG dependency."""
    src = _CONFTEST.read_text(encoding="utf-8")
    assert "async def clean_db" not in src
    assert 'autouse=True)\nasync def clean_db' not in src


@pytest.mark.unit
def test_gate_precedes_dynamic_lifecycle_acquisition() -> None:
    """setup/clickhouse: marker gate до getfixturevalue/lifecycle ensure."""
    src = _CONFTEST.read_text(encoding="utf-8")
    fixtures = _fixture_defs(src)
    for name in ("setup_test_database", "clickhouse_client"):
        body = ast.get_source_segment(src, fixtures[name]) or ""
        gate_pos = body.find("_require_destructive_local")
        resolve_pos = body.find("_resolve_test_infra_lifecycle")
        ensure_pos = body.find("ensure_resources")
        assert gate_pos != -1, name
        assert resolve_pos != -1, name
        assert ensure_pos != -1, name
        assert gate_pos < resolve_pos < ensure_pos, name


@pytest.mark.unit
def test_async_engine_uses_await_dispose() -> None:
    """Teardown AsyncEngine: ``await engine.dispose()``, не sync_engine."""
    src = _CONFTEST.read_text(encoding="utf-8")
    body = ast.get_source_segment(src, _fixture_defs(src)["_async_engine"]) or ""
    assert "await engine.dispose()" in body
    assert "sync_engine.dispose" not in body


@pytest.mark.unit
def test_clickhouse_does_not_depend_on_pg_setup() -> None:
    """CH-only path не тянет setup_test_database."""
    src = _CONFTEST.read_text(encoding="utf-8")
    node = _fixture_defs(src)["clickhouse_client"]
    args = [a.arg for a in node.args.args]
    assert "setup_test_database" not in args
