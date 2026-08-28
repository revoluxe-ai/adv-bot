"""
Сборка MIGRATION_EXECUTION_MANIFEST и graph-aware SOURCE_HISTORY_HASH.

Manifest хеширует revision-файлы, env.py и фиксирует metadata ревизий.
SOURCE_HISTORY_HASH — канонический хеш ancestor closure для набора heads.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_DIR = REPO_ROOT / "alembic_"
VERSIONS_DIR = ALEMBIC_DIR / "versions"
ENV_PY = ALEMBIC_DIR / "env.py"
ALEMBIC_INI = REPO_ROOT / "alembic.ini"


def _revision_dependencies(rev: object) -> object:
    """
    Зависимости ревизии для ancestor closure.

    Alembic ``Script`` exposes ``dependencies`` (not ``depends_on``).
    Module-level ``depends_on`` is used as fallback for tests/fakes.
    """
    deps = getattr(rev, "dependencies", None)
    if deps is not None:
        return deps
    return getattr(rev, "depends_on", None)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _canonical_path(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def build_execution_manifest(
    *,
    release_image_digest: str = "",
    python_version: str = "",
    alembic_version: str = "",
    sqlalchemy_version: str = "",
) -> dict[str, Any]:
    """Строит versioned MIGRATION_EXECUTION_MANIFEST."""
    files: list[dict[str, str]] = []
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        files.append(
            {
                "relative_path": _canonical_path(path),
                "sha256": _file_sha256(path),
            }
        )
    files.append(
        {"relative_path": _canonical_path(ENV_PY), "sha256": _file_sha256(ENV_PY)}
    )
    if ALEMBIC_INI.exists():
        files.append(
            {
                "relative_path": _canonical_path(ALEMBIC_INI),
                "sha256": _file_sha256(ALEMBIC_INI),
            }
        )

    cfg = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(cfg)
    revisions: list[dict[str, Any]] = []
    for rev in script.walk_revisions():
        revisions.append(
            {
                "revision": rev.revision,
                "down_revision": rev.down_revision,
                "depends_on": _revision_dependencies(rev),
                "branch_labels": list(rev.branch_labels or []),
                "file_sha256": _file_sha256(Path(rev.path)),
            }
        )
    revisions.sort(key=lambda r: str(r["revision"]))
    manifest: dict[str, Any] = {
        "manifest_format_version": 1,
        "release_image_digest": release_image_digest,
        "python_version": python_version,
        "alembic_version": alembic_version,
        "sqlalchemy_version": sqlalchemy_version,
        "files": files,
        "revisions": revisions,
        "target_bundle_hash": _hash_obj({"files": files, "revisions": revisions}),
    }
    return manifest


def _hash_obj(obj: object) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ancestor_closure(revision_ids: Iterable[str]) -> set[str]:
    """Каноническая ancestor closure включая down_revision и depends_on."""
    cfg = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(cfg)
    seen: set[str] = set()
    stack = [str(r) for r in revision_ids if str(r) != "BASE"]
    while stack:
        rid = stack.pop()
        if rid in seen:
            continue
        seen.add(rid)
        rev = script.get_revision(rid)
        down = rev.down_revision
        if down is not None:
            if isinstance(down, (list, tuple, set)):
                stack.extend(str(x) for x in cast(Iterable[object], down))
            else:
                stack.append(str(down))
        depends = _revision_dependencies(rev)
        if depends:
            if isinstance(depends, (list, tuple, set)):
                stack.extend(str(x) for x in cast(Iterable[object], depends))
            else:
                stack.append(str(depends))
    return seen


def source_history_hash(revision_ids: Iterable[str]) -> str:
    """SOURCE_HISTORY_HASH по file hashes ancestor closure."""
    closure = sorted(ancestor_closure(revision_ids))
    cfg = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(cfg)
    items: list[dict[str, Any]] = []
    for rid in closure:
        rev = script.get_revision(rid)
        items.append(
            {
                "revision": rid,
                "down_revision": rev.down_revision,
                "depends_on": _revision_dependencies(rev),
                "file_sha256": _file_sha256(Path(rev.path)),
            }
        )
    payload: dict[str, Any] = {"manifest_format_version": 1, "closure": items}
    return _hash_obj(payload)


def main() -> int:
    """CLI: печатает manifest JSON."""
    manifest = build_execution_manifest()
    heads = list(
        ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_heads()
    )
    manifest["source_history_hash_for_heads"] = source_history_hash(heads)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())