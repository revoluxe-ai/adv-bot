"""Unit: fixture gate order for destructive fixtures (fail-closed before side effects).

Проверяет контракт:
``request.node -> require_destructive_local_marker -> validator -> engine/client/docker``.
Все проверки выполняются без реальных подключений/поднятия контейнеров.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.support import destructive_clickhouse

_ROOT_CONFTEST_PATH = Path(__file__).resolve().parents[3] / "conftest.py"
_ROOT_SPEC = importlib.util.spec_from_file_location(
    "_root_conftest_for_fixture_gates",
    _ROOT_CONFTEST_PATH,
)
assert _ROOT_SPEC is not None and _ROOT_SPEC.loader is not None
root_conftest = importlib.util.module_from_spec(_ROOT_SPEC)
_ROOT_SPEC.loader.exec_module(root_conftest)


def _request_without_destructive_marker(fixturename: str) -> pytest.FixtureRequest:
    """Собрать request/node без ``destructive_local`` marker."""

    class _Node:
        keywords: dict[str, object] = {}

        def get_closest_marker(self, _name: str) -> None:
            return None

    return SimpleNamespace(fixturename=fixturename, node=_Node())  # type: ignore[return-value]


def _unwrap_fixture_function(func: object):
    """Взять исходную функцию fixture (pytest оборачивает callable)."""
    return getattr(func, "__wrapped__", func)


@pytest.mark.unit
def test_setup_test_database_requires_marker_before_docker_calls() -> None:
    """setup_test_database: marker fail до любых docker subprocess."""
    request = _request_without_destructive_marker("setup_test_database")
    sync_run = MagicMock()
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    with patch.object(root_conftest, "_sync_run", sync_run):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            gen = setup_fn(request)
            next(gen)
    sync_run.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_engine_requires_marker_before_engine_factory() -> None:
    """async_engine: marker fail до вызова ``_create_test_async_engine``."""
    request = _request_without_destructive_marker("async_engine")
    create_engine = MagicMock()
    async_engine_fn = _unwrap_fixture_function(root_conftest._async_engine)
    with patch.object(root_conftest, "_create_test_async_engine", create_engine):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = async_engine_fn(request, object())
            await anext(agen)
    create_engine.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_session_requires_marker_before_engine_factory() -> None:
    """async_session: marker fail до любых session/engine side effects."""
    request = _request_without_destructive_marker("async_session")
    create_engine = MagicMock()
    async_session_fn = _unwrap_fixture_function(root_conftest._async_session)
    with patch.object(root_conftest, "_create_test_async_engine", create_engine):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = async_session_fn(request, object())
            await anext(agen)
    create_engine.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_postgres_session_requires_marker_before_engine_factory() -> None:
    """postgres_session: marker fail до создания live PG session."""
    request = _request_without_destructive_marker("postgres_session")
    create_engine = MagicMock()
    postgres_session_fn = _unwrap_fixture_function(root_conftest.postgres_session)
    with patch.object(root_conftest, "_create_test_async_engine", create_engine):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = postgres_session_fn(request, object())
            await anext(agen)
    create_engine.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clean_db_requires_marker_before_truncate_engine() -> None:
    """clean_db: marker fail до TRUNCATE engine path."""
    request = _request_without_destructive_marker("clean_db")
    create_engine = MagicMock()
    clean_db_fn = _unwrap_fixture_function(root_conftest.clean_db)
    with (
        patch.object(root_conftest, "_TEST_DB_READY", True),
        patch.object(root_conftest, "_create_test_async_engine", create_engine),
    ):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = clean_db_fn(request)
            await anext(agen)
    create_engine.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complex_adv_requires_marker_before_seed_factory() -> None:
    """complex_adv: marker fail до seed factory/create calls."""
    request = _request_without_destructive_marker("complex_adv")
    seed_factory = AsyncMock()
    complex_adv_fn = _unwrap_fixture_function(root_conftest.complex_adv)
    with patch.object(root_conftest, "create_complex_adv_seed", seed_factory):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = complex_adv_fn(request, AsyncMock())
            await anext(agen)
    seed_factory.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clickhouse_client_requires_marker_before_client_factory() -> None:
    """clickhouse_client: marker fail до ``create_validated_async_clickhouse_client``."""
    request = _request_without_destructive_marker("clickhouse_client")
    client_factory = AsyncMock()
    clickhouse_client_fn = _unwrap_fixture_function(root_conftest.clickhouse_client)
    with patch.object(
        destructive_clickhouse,
        "create_validated_async_clickhouse_client",
        client_factory,
    ):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = clickhouse_client_fn(request, object())
            await anext(agen)
    client_factory.assert_not_awaited()
