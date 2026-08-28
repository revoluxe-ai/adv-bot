"""Mock-only unit tests for destructive integration session lifecycle.

Доказывает cardinality Compose/PG/CH bootstrap, selective startup,
gate-before-side-effect, non-retryable classification и teardown semantics
без реального Docker/PG/CH.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.support.destructive_lifecycle import (
    COMPOSE_SERVICE_CH,
    COMPOSE_SERVICE_PG,
    RetryClass,
    TestInfraLifecycle,
    TestInfraSessionState,
    TestResourceNeeds,
    classify_lifecycle_error,
    discover_resource_needs_from_fixturenames,
    discover_session_resource_needs,
    run_with_bounded_retry,
)
from tests.support.destructive_pg_dsn import DestructiveTestDatabaseError


def _make_sync_mock(*, external_healthy: bool = False):
    """Mock sync_run: external_healthy=True → stack exists before pytest up."""

    state = {"up_done": external_healthy}

    def _sync(*args: object, **_kwargs: object) -> tuple[int, str, str]:
        if "up" in args and "-d" in args:
            state["up_done"] = True
            return 0, "", ""
        if "ps" in args and "-q" in args:
            if not state["up_done"]:
                return 0, "", ""
            return 0, "cid-1\n", ""
        if args[:2] == ("docker", "inspect"):
            return 0, "running healthy", ""
        if "down" in args:
            return 0, "", ""
        return 0, "", ""

    return _sync


def _lifecycle(
    *,
    sync_run=None,
    docker_preflight=None,
    validate_pg=None,
    validate_ch=None,
    init_pg=None,
    init_ch=None,
    raise_stage=None,
    sleep_fn=None,
    reuse_mode: bool = False,
    startup_max_retries: int = 3,
    settle_sleep_sec: float = 0.0,
) -> TestInfraLifecycle:
    """Собрать lifecycle с mock runners."""
    import os

    os.environ.setdefault("ALLOW_DESTRUCTIVE_TEST_SUBPROCESS", "1")

    def _default_raise(**kwargs):
        raise RuntimeError(
            f"DOCKER_STAGE={kwargs.get('stage')}; exit_code={kwargs.get('exit_code')}"
        )

    state = TestInfraSessionState(reuse_mode=reuse_mode)
    return TestInfraLifecycle(
        state=state,
        compose_file="tests/docker-compose.test.yml",
        sync_run=sync_run or MagicMock(side_effect=_make_sync_mock()),
        docker_preflight=docker_preflight or MagicMock(return_value=["docker", "compose"]),
        validate_pg=validate_pg or MagicMock(),
        validate_ch=validate_ch or MagicMock(),
        init_pg_schema=init_pg or MagicMock(),
        init_ch_schema=init_ch or MagicMock(),
        raise_docker_stage=raise_stage or _default_raise,
        sleep_fn=sleep_fn or MagicMock(),
        startup_max_retries=startup_max_retries,
        startup_sleep_sec=0.01,
        settle_sleep_sec=settle_sleep_sec,
        init_max_retries=3,
    )


@pytest.mark.unit
def test_resource_discovery_from_fixturenames() -> None:
    """PG/CH fixtures → корректные needs; unit fixtures → no compose."""
    assert discover_resource_needs_from_fixturenames(
        ["async_session", "tmp_path"]
    ) == TestResourceNeeds(needs_pg=True, needs_clickhouse=False)
    assert discover_resource_needs_from_fixturenames(
        ["clickhouse_client"]
    ) == TestResourceNeeds(needs_pg=False, needs_clickhouse=True)
    assert discover_resource_needs_from_fixturenames(
        ["async_session", "clickhouse_client"]
    ) == TestResourceNeeds(needs_pg=True, needs_clickhouse=True)
    empty = discover_resource_needs_from_fixturenames(["tmp_path", "monkeypatch"])
    assert empty.needs_compose is False


@pytest.mark.unit
def test_session_resource_union() -> None:
    """Union по items даёт mixed selection."""
    items = [
        SimpleNamespace(fixturenames=["async_session"]),
        SimpleNamespace(fixturenames=["clickhouse_client"]),
        SimpleNamespace(fixturenames=["tmp_path"]),
    ]
    needs = discover_session_resource_needs(items)
    assert needs.needs_pg and needs.needs_clickhouse
    assert needs.compose_services == (COMPOSE_SERVICE_PG, COMPOSE_SERVICE_CH)


@pytest.mark.unit
def test_lifecycle_cardinality_for_n_pg_tests() -> None:
    """N PG ensures → compose/pg bootstrap once; data reset N times."""
    init_pg = MagicMock()
    sync_run = MagicMock(side_effect=_make_sync_mock())
    lc = _lifecycle(sync_run=sync_run, init_pg=init_pg)
    n = 5
    for _ in range(n):
        lc.ensure_resources(TestResourceNeeds(needs_pg=True))
        lc.record_pg_data_reset()
    assert COMPOSE_SERVICE_PG in lc.state.started_services
    assert COMPOSE_SERVICE_CH not in lc.state.started_services
    lc.teardown()
    assert lc.state.compose_up_count == 1
    assert lc.state.compose_down_count == 1
    assert lc.state.pg_schema_init_count == 1
    assert init_pg.call_count == 1
    assert lc.state.pg_data_reset_count == n
    assert lc.state.clickhouse_schema_init_count == 0


@pytest.mark.unit
def test_lifecycle_cardinality_ch_only() -> None:
    """CH-only → start test_clickhouse, not test_db."""
    init_ch = MagicMock()
    init_pg = MagicMock()
    lc = _lifecycle(init_ch=init_ch, init_pg=init_pg)
    for _ in range(3):
        lc.ensure_resources(TestResourceNeeds(needs_clickhouse=True))
        lc.record_ch_data_reset()
    assert COMPOSE_SERVICE_PG not in lc.state.started_services
    assert COMPOSE_SERVICE_CH in lc.state.started_services
    lc.teardown()
    assert lc.state.compose_up_count == 1
    assert lc.state.compose_down_count == 1
    assert init_ch.call_count == 1
    assert init_pg.call_count == 0
    assert lc.state.clickhouse_data_reset_count == 3


@pytest.mark.unit
def test_lifecycle_mixed_one_compose() -> None:
    """Mixed PG+CH → один compose up, оба bootstrap."""
    lc = _lifecycle()
    lc.ensure_resources(TestResourceNeeds(needs_pg=True, needs_clickhouse=True))
    assert COMPOSE_SERVICE_PG in lc.state.started_services
    assert COMPOSE_SERVICE_CH in lc.state.started_services
    lc.teardown()
    assert lc.state.compose_up_count == 1
    assert lc.state.compose_down_count == 1
    assert lc.state.pg_schema_init_count == 1
    assert lc.state.clickhouse_schema_init_count == 1


@pytest.mark.unit
def test_unit_only_selection_no_compose() -> None:
    """needs_compose=False → никаких side effects."""
    preflight = MagicMock()
    sync_run = MagicMock()
    lc = _lifecycle(docker_preflight=preflight, sync_run=sync_run)
    lc.ensure_resources(TestResourceNeeds())
    lc.teardown()
    preflight.assert_not_called()
    sync_run.assert_not_called()
    assert lc.state.compose_up_count == 0
    assert lc.state.compose_down_count == 0


@pytest.mark.unit
def test_validation_failure_before_compose() -> None:
    """Deterministic validator → compose not called, sleep not called, once."""
    validate_pg = MagicMock(
        side_effect=DestructiveTestDatabaseError("DEV_TUNNELS_KUBECONFIG is set")
    )
    preflight = MagicMock()
    sync_run = MagicMock()
    sleep = MagicMock()
    lc = _lifecycle(
        validate_pg=validate_pg,
        docker_preflight=preflight,
        sync_run=sync_run,
        sleep_fn=sleep,
    )
    with pytest.raises(DestructiveTestDatabaseError, match="DEV_TUNNELS_KUBECONFIG"):
        lc.ensure_resources(TestResourceNeeds(needs_pg=True))
    validate_pg.assert_called_once()
    preflight.assert_not_called()
    sync_run.assert_not_called()
    sleep.assert_not_called()
    assert lc.state.compose_up_count == 0


@pytest.mark.unit
def test_missing_subprocess_opt_in_before_compose() -> None:
    """Missing destructive subprocess/DB/CH opt-in → no compose."""
    import os
    from unittest.mock import patch

    preflight = MagicMock()
    sync_run = MagicMock()
    lc = _lifecycle(docker_preflight=preflight, sync_run=sync_run)
    with patch.dict(
        os.environ,
        {
            "ALLOW_DESTRUCTIVE_TEST_SUBPROCESS": "0",
            "ALLOW_DESTRUCTIVE_TEST_DB": "0",
            "ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE": "0",
        },
        clear=False,
    ):
        with pytest.raises(RuntimeError, match="ALLOW_DESTRUCTIVE_TEST_SUBPROCESS"):
            lc.ensure_resources(TestResourceNeeds(needs_pg=True))
    preflight.assert_not_called()
    sync_run.assert_not_called()


@pytest.mark.unit
def test_ch_validation_failure_before_compose() -> None:
    """Invalid CH endpoint → no compose."""
    from tests.support.destructive_clickhouse import DestructiveTestClickHouseError

    validate_ch = MagicMock(
        side_effect=DestructiveTestClickHouseError("port not allowlisted")
    )
    preflight = MagicMock()
    sync_run = MagicMock()
    lc = _lifecycle(
        validate_ch=validate_ch, docker_preflight=preflight, sync_run=sync_run
    )
    with pytest.raises(DestructiveTestClickHouseError):
        lc.ensure_resources(TestResourceNeeds(needs_clickhouse=True))
    preflight.assert_not_called()
    sync_run.assert_not_called()


@pytest.mark.unit
def test_deterministic_error_no_retry() -> None:
    """NON_RETRYABLE → one call, no sleep."""
    sleep = MagicMock()
    op = MagicMock(side_effect=DestructiveTestDatabaseError("refuse connect"))
    with pytest.raises(DestructiveTestDatabaseError):
        run_with_bounded_retry(op, max_attempts=5, sleep_fn=sleep)
    assert op.call_count == 1
    sleep.assert_not_called()
    assert classify_lifecycle_error(DestructiveTestDatabaseError("x")) is RetryClass.NON_RETRYABLE


@pytest.mark.unit
def test_transient_retry_then_success() -> None:
    """Transient → bounded retry, success without excess."""
    sleep = MagicMock()
    calls = {"n": 0}

    def _op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("connection refused")
        return "ok"

    assert run_with_bounded_retry(_op, max_attempts=5, sleep_fn=sleep) == "ok"
    assert calls["n"] == 3
    assert sleep.call_count == 2


@pytest.mark.unit
def test_retry_budget_exhaustion() -> None:
    """Исчерпание retry → final error; no secrets in classification path."""
    sleep = MagicMock()
    op = MagicMock(side_effect=ConnectionError("refused password=secret"))
    with pytest.raises(ConnectionError, match="refused"):
        run_with_bounded_retry(op, max_attempts=3, sleep_fn=sleep)
    assert op.call_count == 3
    assert sleep.call_count == 2


@pytest.mark.unit
def test_teardown_preserves_primary_failure() -> None:
    """Teardown cleanup error не заменяет primary failure."""
    sync_state = {"up_done": False}

    def _sync(*args, **_kwargs):
        if "up" in args and "-d" in args:
            sync_state["up_done"] = True
            return 0, "", ""
        if "down" in args:
            return 9, "", "cleanup TOKEN=secret"
        if "ps" in args and "-q" in args:
            if not sync_state["up_done"]:
                return 0, "", ""
            return 0, "cid\n", ""
        if args[:2] == ("docker", "inspect"):
            return 0, "running healthy", ""
        return 0, "", ""

    def _raise(**kwargs):
        raise RuntimeError(
            f"DOCKER_STAGE={kwargs['stage']}; exit_code={kwargs['exit_code']}; "
            f"stderr={kwargs.get('stderr')}"
        )

    lc = _lifecycle(sync_run=MagicMock(side_effect=_sync), raise_stage=_raise)
    lc.ensure_resources(TestResourceNeeds(needs_pg=True))
    # primary present → cleanup warning, no raise
    lc.teardown(primary_exception=RuntimeError("primary boom"))
    assert lc.state.compose_down_count == 1


@pytest.mark.unit
def test_teardown_raises_cleanup_when_no_primary() -> None:
    """Без primary cleanup error обязан подняться."""
    sync_state = {"up_done": False}

    def _sync(*args, **_kwargs):
        if "up" in args and "-d" in args:
            sync_state["up_done"] = True
            return 0, "", ""
        if "down" in args:
            return 2, "", "cleanup failed"
        if "ps" in args and "-q" in args:
            if not sync_state["up_done"]:
                return 0, "", ""
            return 0, "cid\n", ""
        if args[:2] == ("docker", "inspect"):
            return 0, "running healthy", ""
        return 0, "", ""

    def _raise(**kwargs):
        raise RuntimeError(f"DOCKER_STAGE={kwargs['stage']}; exit_code={kwargs['exit_code']}")

    lc = _lifecycle(sync_run=MagicMock(side_effect=_sync), raise_stage=_raise)
    lc.ensure_resources(TestResourceNeeds(needs_pg=True))
    with pytest.raises(RuntimeError, match="DOCKER_STAGE=cleanup"):
        lc.teardown()


@pytest.mark.unit
def test_reuse_mode_skips_compose_down() -> None:
    """TEST_INFRA_REUSE: pytest не останавливает containers."""
    sync_run = MagicMock(side_effect=_make_sync_mock())
    lc = _lifecycle(sync_run=sync_run, reuse_mode=True)
    lc.ensure_resources(TestResourceNeeds(needs_pg=True))
    lc.teardown()
    down_calls = [c for c in sync_run.call_args_list if "down" in c.args]
    assert down_calls == []
    assert lc.state.compose_down_count == 0


@pytest.mark.unit
def test_teardown_skips_compose_down_when_external_stack_already_healthy() -> None:
    """FP-001: /opsx-test-env external stack must survive pytest session teardown.

    When compose services are already healthy before ``ensure_resources``,
    lifecycle reuses them (``up -d`` without force-recreate) but must not
    claim pytest ownership — session teardown must not run ``compose down -v``.
    """
    down_calls: list[tuple[object, ...]] = []

    def _sync(*args: object, **_kwargs: object) -> tuple[int, str, str]:
        if "down" in args:
            down_calls.append(args)
            return 0, "", ""
        if "ps" in args and "-q" in args:
            return 0, "external-cid\n", ""
        if args[:2] == ("docker", "inspect"):
            return 0, "running healthy", ""
        if "up" in args:
            return 0, "", ""
        return 0, "", ""

    lc = _lifecycle(sync_run=MagicMock(side_effect=_sync))
    lc.ensure_resources(TestResourceNeeds(needs_pg=True))
    assert lc.state.compose_up_count == 1
    assert lc.state.compose_started_by_pytest is False
    lc.teardown()
    assert down_calls == [], (
        "must not compose down externally-owned /opsx-test-env stack"
    )
    assert lc.state.compose_down_count == 0


@pytest.mark.unit
def test_partial_startup_tracks_started_services() -> None:
    """После успешного PG health service отмечен started."""
    lc = _lifecycle()
    lc.ensure_resources(TestResourceNeeds(needs_pg=True))
    assert COMPOSE_SERVICE_PG in lc.state.started_services
    assert lc.state.health_check_counts.get(COMPOSE_SERVICE_PG) == 1


@pytest.mark.unit
def test_run_awaitable_from_sync_without_running_loop() -> None:
    """Без running loop bridge использует asyncio.run и возвращает результат."""
    from tests.support.destructive_lifecycle import run_awaitable_from_sync

    async def _work() -> str:
        return "ok"

    assert run_awaitable_from_sync(_work()) == "ok"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_awaitable_from_sync_inside_running_loop() -> None:
    """Regression: schema bootstrap из async fixture не должен звать голый asyncio.run.

    Симулирует ``clickhouse_client`` → ``ensure_resources`` → init_*_schema:
    уже есть running loop; прямой ``asyncio.run`` падает, bridge — нет.
    """
    import asyncio

    from tests.support.destructive_lifecycle import run_awaitable_from_sync

    async def _work() -> int:
        await asyncio.sleep(0)
        return 42

    doomed = _work()
    with pytest.raises(RuntimeError, match="running event loop"):
        asyncio.run(doomed)
    doomed.close()

    assert run_awaitable_from_sync(_work()) == 42


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_resources_ch_init_ok_under_running_loop() -> None:
    """ensure_resources(CH) с init, использующим bridge, не падает под async loop."""
    from tests.support.destructive_lifecycle import run_awaitable_from_sync

    calls: list[str] = []

    def _init_ch() -> None:
        async def _ddl() -> None:
            calls.append("ddl")

        run_awaitable_from_sync(_ddl())

    lc = _lifecycle(init_ch=_init_ch)
    lc.ensure_resources(TestResourceNeeds(needs_clickhouse=True))
    assert calls == ["ddl"]
    assert lc.state.clickhouse_schema_initialized is True
    assert lc.state.clickhouse_schema_init_count == 1
