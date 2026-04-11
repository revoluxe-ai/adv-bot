"""HTTP entrypoint is always up with uvicorn; lifespan bot hooks are mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_ok_when_lifespan_bot_hooks_mocked() -> None:
    import client_bot_run

    async def _noop(*_args: object, **_kwargs: object) -> None:
        return None

    with (
        patch.object(client_bot_run, "POLLING_MODE", False),
        patch.object(
            client_bot_run,
            "configure_webhook_for_production",
            new=AsyncMock(),
        ),
        patch.object(
            client_bot_run,
            "initialize_token_monitoring",
            new=AsyncMock(),
        ),
        patch.object(
            client_bot_run,
            "shutdown_token_monitoring",
            new=AsyncMock(),
        ),
    ):
        with TestClient(client_bot_run.app, raise_server_exceptions=True) as client:
            resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK"}
