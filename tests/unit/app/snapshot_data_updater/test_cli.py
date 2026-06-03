"""Unit-тесты CLI entrypoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_cli_smoke_returns_zero() -> None:
    async def _noop() -> None:
        return None

    with patch("app.snapshot_data_updater.cli._bootstrap_env"):
        with patch("asyncio.run", side_effect=lambda coro: coro.close()) as mock_run:
            with patch("app.snapshot_data_updater.cli._cmd_smoke", _noop):
                from app.snapshot_data_updater.cli import main

                code = main(["smoke"])
    assert code == 0
    mock_run.assert_called_once()
