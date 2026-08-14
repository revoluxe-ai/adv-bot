from __future__ import annotations

from pathlib import Path

import opsx_conflict.runtime as runtime


def test_runtime_has_no_unstage_or_restore_rollback_action() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    assert "restore --staged" not in source
    assert "def unstage" not in source
