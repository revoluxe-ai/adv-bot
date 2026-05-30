"""Unit: V3 ladder selection must not call key-level ``passes_rec_gate_for_up``."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_V3_ROOT = _REPO_ROOT / "app" / "modules" / "shop_runner" / "service_manager" / "services" / "auto_updater_v3"

_ALLOWED_FILES = frozenset(
    {
        "transition_ranking.py",  # legacy definition + docstring
    }
)


@pytest.mark.unit
def test_v3_modules_do_not_call_passes_rec_gate_for_up_in_selection() -> None:
    """Grep guard: selection paths use ``state_passes_rec_gate_for_mode`` only."""
    offenders: list[str] = []
    for path in sorted(_V3_ROOT.rglob("*.py")):
        if path.name in _ALLOWED_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        if "passes_rec_gate_for_up(" not in text:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if "passes_rec_gate_for_up(" in stripped and not stripped.startswith("#"):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{i}")
    assert offenders == [], f"key-level rec_gate in V3: {offenders}"
