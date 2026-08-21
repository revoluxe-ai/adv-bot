"""Gate-before-infra: missing marker/opt-in → no compose/engine/client factory."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.support import destructive_clickhouse
from tests.support.destructive_pg_dsn import DestructiveTestDatabaseError

_ROOT_CONFTEST_PATH = Path(__file__).resolve().parents[3] / "conftest.py"
_ROOT_SPEC = importlib.util.spec_from_file_location(
    "_root_conftest_for_fixture_gates",
    _ROOT_CONFTEST_PATH,
)
assert _ROOT_SPEC is not None and _ROOT_SPEC.loader is not None
root_conftest = importlib.util.module_from_spec(_ROOT_SPEC)
_ROOT_SPEC.loader.exec_module(root_conftest)


def _unwrap_fixture_function(func: object):
    return getattr(func, "__wrapped__", func)


def _request_without_destructive_marker(fixturename: str) -> pytest.FixtureRequest:
    class _Node:
        keywords: dict[str, object] = {}

        def get_closest_marker(self, _name: str) -> None:
            return None

    return SimpleNamespace(fixturename=fixturename, node=_Node())  # type: ignore[return-value]


def _request_with_destructive_marker(fixturename: str) -> pytest.FixtureRequest:
    class _Marker:
        pass

    class _Node:
        keywords: dict[str, object] = {"destructive_local": True}

        def get_closest_marker(self, name: str):
            return _Marker() if name == "destructive_local" else None

    return SimpleNamespace(fixturename=fixturename, node=_Node())  # type: ignore[return-value]


@pytest.mark.unit
def test_setup_test_database_requires_marker_before_docker_calls() -> None:
    """setup_test_database: marker fail до lifecycle/docker."""
    request = _request_without_destructive_marker("setup_test_database")
    sync_run = MagicMock()
    lifecycle = MagicMock()
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    with (
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest, "_resolve_test_infra_lifecycle", MagicMock(return_value=lifecycle)),
        patch.object(root_conftest, "_validate_pg_preflight", MagicMock()),
    ):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            gen = setup_fn(request)
            next(gen)
    sync_run.assert_not_called()
    lifecycle.ensure_resources.assert_not_called()


@pytest.mark.unit
def test_setup_missing_opt_in_before_lifecycle() -> None:
    """Missing ALLOW_DESTRUCTIVE_TEST_DB → no lifecycle ensure."""
    request = _request_with_destructive_marker("setup_test_database")
    lifecycle = MagicMock()
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    with (
        patch.dict(
            "os.environ",
            {
                "ALLOW_DESTRUCTIVE_TEST_DB": "0",
                "DEV_TUNNELS_ENABLED": "false",
                "DEV_TUNNELS_KUBECONFIG": "",
                # Isolates from ambient / leaked suite pollution (TUNNEL_PRESENT_ENV_KEYS).
                "DEV_TUNNEL_PG_LOCAL_PORT": "",
                "DEV_TUNNEL_CH_HTTP_PORT": "",
            },
            clear=False,
        ),
        patch.object(
            root_conftest,
            "_resolve_test_infra_lifecycle",
            MagicMock(return_value=lifecycle),
        ),
    ):
        with pytest.raises(DestructiveTestDatabaseError, match="opt-in"):
            gen = setup_fn(request)
            next(gen)
    lifecycle.ensure_resources.assert_not_called()


@pytest.mark.unit
def test_setup_tunnel_env_before_lifecycle() -> None:
    """DEV_TUNNELS_KUBECONFIG → fail before compose.

    Явно гасим ambient DEV_TUNNELS_ENABLED и прочие present-keys, иначе
    validator сначала ругается на truthy-flag и match по KUBECONFIG флакает.
    """
    request = _request_with_destructive_marker("setup_test_database")
    lifecycle = MagicMock()
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    with (
        patch.dict(
            "os.environ",
            {
                "ALLOW_DESTRUCTIVE_TEST_DB": "1",
                "DEV_TUNNELS_ENABLED": "false",
                # Isolates from ambient / leaked suite pollution (TUNNEL_PRESENT_ENV_KEYS).
                "DEV_TUNNELS_KUBECONFIG": "/tmp/kube",
                "DEV_TUNNEL_PG_LOCAL_PORT": "",
                "DEV_TUNNEL_CH_HTTP_PORT": "",
            },
            clear=False,
        ),
        patch.object(
            root_conftest,
            "_resolve_test_infra_lifecycle",
            MagicMock(return_value=lifecycle),
        ),
    ):
        with pytest.raises(DestructiveTestDatabaseError, match="DEV_TUNNELS_KUBECONFIG"):
            gen = setup_fn(request)
            next(gen)
    lifecycle.ensure_resources.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_engine_requires_marker_before_engine_factory() -> None:
    request = _request_without_destructive_marker("async_engine")
    create_engine = MagicMock()
    async_engine_fn = _unwrap_fixture_function(root_conftest._async_engine)
    with patch.object(root_conftest, "_create_test_async_engine", create_engine):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = async_engine_fn(request, object(), object())
            await anext(agen)
    create_engine.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_session_requires_marker_before_engine_factory() -> None:
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
async def test_complex_adv_requires_marker_before_seed_factory() -> None:
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
    request = _request_without_destructive_marker("clickhouse_client")
    client_factory = AsyncMock()
    lifecycle = MagicMock()
    lifecycle.state.clickhouse_schema_initialized = True
    clickhouse_client_fn = _unwrap_fixture_function(root_conftest.clickhouse_client)
    with (
        patch.object(
            destructive_clickhouse,
            "create_validated_async_clickhouse_client",
            client_factory,
        ),
        patch.object(
            root_conftest,
            "_resolve_test_infra_lifecycle",
            MagicMock(return_value=lifecycle),
        ),
        patch.object(root_conftest, "_validate_ch_preflight", MagicMock()),
    ):
        with pytest.raises(pytest.fail.Exception, match="destructive_local"):
            agen = clickhouse_client_fn(request)
            await anext(agen)
    client_factory.assert_not_awaited()
    lifecycle.ensure_resources.assert_not_called()
