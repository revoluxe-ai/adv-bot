"""Fail-closed porcelain-v2 parser regression tests."""

from __future__ import annotations

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.operation import parse_porcelain_v2_z


def test_paths_with_spaces_and_rename_pair_are_parsed() -> None:
    raw = (
        "1 M. N... 100644 100644 100644 aaaaaaa bbbbbbb path with spaces.py\0"
        "2 .M N... 100644 100644 100644 aaaaaaa bbbbbbb R100 new name.py\0"
        "old name.py\0"
        "? untracked name.txt\0"
    )
    staged, unstaged, untracked = parse_porcelain_v2_z(raw)
    assert staged == ["path with spaces.py"]
    assert unstaged == ["new name.py"]
    assert untracked == ["untracked name.txt"]


@pytest.mark.parametrize(
    "raw",
    [
        "1 M. too-short\0",
        "2 R. too-short\0",
        "2 R. N... 100644 100644 100644 aaaaaaa bbbbbbb R100 new.py\0",
        "! ignored-record.py\0",
    ],
)
def test_malformed_or_unknown_records_stop(raw: str) -> None:
    with pytest.raises(StopRequired):
        parse_porcelain_v2_z(raw)
