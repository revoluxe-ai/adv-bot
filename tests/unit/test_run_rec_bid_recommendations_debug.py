"""Unit tests for the read-only rec bid debug entrypoint."""

from __future__ import annotations

import pytest

import run_rec_bid_recommendations_debug as entrypoint


@pytest.mark.unit
def test_run_ensures_dev_tunnels_before_first_env_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _ensure() -> None:
        calls.append("ensure_dev_tunnels")

    def _required_env(_name: str) -> str:
        calls.append("required_env")
        raise SystemExit("stop after first env read")

    monkeypatch.setattr(entrypoint, "_ensure_dev_tunnels", _ensure)
    monkeypatch.setattr(entrypoint, "_required_env", _required_env)

    with pytest.raises(SystemExit, match="stop after first env read"):
        entrypoint.asyncio.run(entrypoint._run())

    assert calls == ["ensure_dev_tunnels", "required_env"]
