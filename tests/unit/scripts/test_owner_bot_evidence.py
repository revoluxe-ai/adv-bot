"""Unit tests для shared Owner-bot evidence plane loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.wb_api_readonly_ops.collect import owner_bot_evidence


@pytest.mark.unit
def test_fullstats_loader_source_forbids_get_fullstats() -> None:
    """Regression: только supported ``_request_chunk``, не orphan ``get_fullstats``."""
    source = Path(owner_bot_evidence.__file__).read_text(encoding="utf-8")
    assert "get_fullstats" not in source
    assert "_request_chunk" in source


@pytest.mark.unit
def test_job_scoped_runtime_source_avoids_module_read_only_engine() -> None:
    """Strict Job path не использует module-level engine/session factory."""
    source = Path(owner_bot_evidence.__file__).read_text(encoding="utf-8")
    assert "session_maker.read_only_engine" not in source
    assert "read_write_engine" not in source
    assert "get_async_session_maker" not in source
    assert "job_read_only_session" in source


@pytest.mark.unit
def test_job_scoped_runtime_open_close_cycle() -> None:
    """Plane runtime закрывает loop без повторного asyncio.run."""
    runtime = owner_bot_evidence.JobScopedEvidenceRuntime()
    assert not runtime.loop.is_closed()

    async def _noop() -> int:
        return 1

    assert runtime.run(_noop()) == 1
    runtime.close()
    assert runtime.loop.is_closed()


@pytest.mark.unit
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_run_after_close_fail_closed() -> None:
    """После ``close()`` повторный ``run()`` запрещён."""
    runtime = owner_bot_evidence.JobScopedEvidenceRuntime()
    runtime.close()

    async def _noop() -> int:
        return 0

    with pytest.raises(owner_bot_evidence.JobScopedEvidenceRuntimeClosedError):
        runtime.run(_noop())


@pytest.mark.unit
def test_same_loop_real_sqlalchemy_engine_open_close() -> None:
    """Job loop: create real AsyncEngine → dispose на том же loop без ошибки."""
    from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

    def _real_engine() -> AsyncEngine:
        return create_async_engine(
            "postgresql+asyncpg://job_local:x@127.0.0.1:59999/none",
            pool_pre_ping=False,
        )

    with patch.object(
        owner_bot_evidence,
        "_create_job_read_only_engine",
        side_effect=_real_engine,
    ):
        runtime = owner_bot_evidence.JobScopedEvidenceRuntime()

        async def _open_factory() -> int:
            runtime._ensure_pg_factory()
            assert runtime.pg_engine is not None
            return id(runtime.pg_engine)

        engine_id = runtime.run(_open_factory())
        runtime.close()
        assert runtime.loop.is_closed()
        assert engine_id != id(None)


@pytest.mark.unit
def test_cross_loop_runtimes_do_not_share_job_local_pg_engine() -> None:
    """Runtime A/B: отдельные real AsyncEngine; global singleton был бы одним id."""
    from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

    from app.utils.db.session_maker import read_only_engine as module_read_only_engine

    created: list[AsyncEngine] = []

    def _real_engine() -> AsyncEngine:
        engine = create_async_engine(
            f"postgresql+asyncpg://job{len(created)}:x@127.0.0.1:59999/none",
            pool_pre_ping=False,
        )
        created.append(engine)
        return engine

    with patch.object(
        owner_bot_evidence,
        "_create_job_read_only_engine",
        side_effect=_real_engine,
    ):
        runtime_a = owner_bot_evidence.JobScopedEvidenceRuntime()
        runtime_b = owner_bot_evidence.JobScopedEvidenceRuntime()

        async def _touch(runtime: owner_bot_evidence.JobScopedEvidenceRuntime) -> int:
            runtime._ensure_pg_factory()
            assert runtime.pg_engine is not None
            return id(runtime.pg_engine)

        engine_id_a = runtime_a.run(_touch(runtime_a))
        engine_id_b = runtime_b.run(_touch(runtime_b))
        assert engine_id_a != engine_id_b
        assert len(created) == 2
        assert isinstance(created[0], AsyncEngine)
        assert isinstance(created[1], AsyncEngine)
        # Старый путь module singleton дал бы один и тот же engine для A и B.
        assert id(module_read_only_engine) == id(module_read_only_engine)
        assert engine_id_a != id(module_read_only_engine)

        runtime_a.close()
        runtime_b.close()


@pytest.mark.unit
def test_cross_loop_asyncio_future_misuse_fails_on_foreign_loop() -> None:
    """Loop-bound Future с runtime A нельзя await на loop B (аналог global pool misuse)."""
    runtime_a = owner_bot_evidence.JobScopedEvidenceRuntime()
    runtime_b = owner_bot_evidence.JobScopedEvidenceRuntime()
    foreign_future = runtime_a.loop.create_future()

    async def _await_foreign() -> None:
        await foreign_future

    with pytest.raises(RuntimeError, match="Future|loop|event loop"):
        runtime_b.run(_await_foreign())

    runtime_a.close()
    runtime_b.close()


@pytest.mark.unit
def test_close_propagates_dispose_failure() -> None:
    """``close()`` не глотает ошибки dispose Job-local engine."""
    runtime = owner_bot_evidence.JobScopedEvidenceRuntime()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock(side_effect=RuntimeError("dispose failed"))
    runtime._pg_engine = mock_engine
    runtime._pg_session_maker = MagicMock()

    with pytest.raises(RuntimeError, match="dispose failed"):
        runtime.close()
    assert runtime.loop.is_closed()


@pytest.mark.unit
def test_evidence_reader_failure_is_typed_exception() -> None:
    """EvidenceReaderFailure несёт source/phase для GAP provenance."""
    exc = owner_bot_evidence.EvidenceReaderFailure(
        section="orders",
        source="owner-bot-wb-evidence",
        phase="wb_load",
        error_class="RuntimeError",
        message="loop closed",
    )
    text = str(exc)
    assert "source=owner-bot-wb-evidence" in text
    assert "phase=wb_load" in text
    assert exc.error_class == "RuntimeError"
