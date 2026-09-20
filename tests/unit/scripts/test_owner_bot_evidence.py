"""Unit tests для shared Owner-bot evidence plane loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.wb_api_readonly_ops.collect import owner_bot_evidence


@pytest.mark.unit
def test_fullstats_loader_source_forbids_get_fullstats() -> None:
    """Regression: только supported ``_request_chunk``, не orphan ``get_fullstats``."""
    source = Path(owner_bot_evidence.__file__).read_text(encoding="utf-8")
    assert "get_fullstats" not in source
    assert "_request_chunk" in source


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
