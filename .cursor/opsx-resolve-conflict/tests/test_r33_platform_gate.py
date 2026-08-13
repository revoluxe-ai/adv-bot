"""R33: ADR-OPSX-RC-PLATFORM-001 Windows-only platform gate."""

from __future__ import annotations

import pytest

import opsx_conflict.attestation as att
from opsx_conflict.attestation import assert_supported_platform
from opsx_conflict.errors import StopRequired


def test_windows_platform_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows hosts pass the supported-platform gate."""
    monkeypatch.setattr(att, "_host_is_windows", lambda: True)
    assert_supported_platform()


def test_non_windows_platform_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Linux/macOS hosts raise typed UNSUPPORTED_PLATFORM."""
    monkeypatch.setattr(att, "_host_is_windows", lambda: False)
    with pytest.raises(StopRequired) as exc:
        assert_supported_platform()
    assert exc.value.reason == "UNSUPPORTED_PLATFORM"
    assert exc.value.details["decision_id"] == "ADR-OPSX-RC-PLATFORM-001"
    assert exc.value.details["disposition"] == "WINDOWS_PREVIEW_ONLY"
    assert "windows" in exc.value.details["supported_platforms"]
