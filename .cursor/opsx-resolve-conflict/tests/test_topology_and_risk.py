from __future__ import annotations

from opsx_conflict.runtime import (
    classify_path_risk,
    detect_directory_renames,
    parse_name_status,
)


def test_directory_rename_detected_from_multiple_coherent_renames() -> None:
    raw = "\n".join(
        [
            "R100\told/a.py\tnew/a.py",
            "R095\told/b.py\tnew/b.py",
            "M\tconsumer.py",
        ]
    )
    changes = parse_name_status(raw)
    dirs = detect_directory_renames(changes)
    assert len(dirs) == 1
    assert dirs[0]["type"] == "directory-rename"
    assert dirs[0]["old_dir"] == "old"
    assert dirs[0]["new_dir"] == "new"
    assert classify_path_risk("new/a.py", topology="directory-rename") == "HIGH"


def test_process_migration_and_lock_paths_are_high() -> None:
    assert classify_path_risk(".cursor/commands/x.md") == "HIGH"
    assert classify_path_risk("alembic_/versions/abc.py") == "HIGH"
    assert classify_path_risk("poetry.lock") == "HIGH"
