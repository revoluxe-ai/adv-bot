"""Path confinement helpers — reject traversal / sibling-prefix escape (CF-001).

Read-oriented resolution never creates directories. Write preparation is an
explicit separate API used only after scope authorization.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from .errors import PolicyViolation, StopRequired


def normalize_repo_rel(path: str | Path) -> str:
    """Normalize to a relative POSIX path; reject absolute/.. /UNC /drive forms."""
    text = str(path).replace("\\", "/")
    if not text or text.strip() != text:
        raise PolicyViolation("empty or whitespace path")
    if text.startswith("//") or text.startswith("\\\\"):
        raise PolicyViolation("UNC path forbidden")
    pure_win = PureWindowsPath(text)
    if pure_win.drive or pure_win.root:
        raise PolicyViolation("absolute/drive path forbidden")
    pure = PurePosixPath(text)
    if pure.is_absolute():
        raise PolicyViolation("absolute path forbidden")
    parts = [p for p in pure.parts if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise PolicyViolation("parent traversal forbidden")
    if any(p.startswith("/") for p in parts):
        raise PolicyViolation("absolute path fragment forbidden")
    return "/".join(parts)


def _assert_symlink_chain(root: Path, rel: str) -> None:
    cur = root
    for part in PurePosixPath(rel).parts[:-1]:
        cur = cur / part
        if not cur.exists() and not cur.is_symlink():
            return
        if cur.is_symlink():
            linked = cur.resolve(strict=False)
            try:
                linked.relative_to(root)
            except ValueError as exc:
                raise StopRequired(
                    "SYMLINK_ESCAPE_BLOCKED",
                    {"path": rel, "link": str(cur), "target": str(linked)},
                ) from exc


def resolve_existing_under_repo(
    repo_root: Path,
    rel_path: str | Path,
) -> tuple[str, Path]:
    """Resolve an existing path under the repo without creating parents."""
    rel = normalize_repo_rel(rel_path)
    root = repo_root.resolve(strict=True)
    candidate = root / rel
    if not candidate.exists() and not candidate.is_symlink():
        raise StopRequired("PATH_NOT_FOUND", {"path": rel})
    target = candidate.resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise StopRequired(
            "PATH_ESCAPE_BLOCKED",
            {"path": rel, "resolved": str(target), "repo": str(root)},
        ) from exc
    _assert_symlink_chain(root, rel)
    return rel, target


def prepare_new_path_under_repo(
    repo_root: Path,
    rel_path: str | Path,
) -> tuple[str, Path]:
    """Prepare parents for a new write target after scope authorization."""
    rel = normalize_repo_rel(rel_path)
    root = repo_root.resolve(strict=True)
    candidate = root / rel
    parent = candidate.parent
    parent.mkdir(parents=True, exist_ok=True)
    target = parent.resolve(strict=True) / candidate.name
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise StopRequired(
            "PATH_ESCAPE_BLOCKED",
            {"path": rel, "resolved": str(target), "repo": str(root)},
        ) from exc
    _assert_symlink_chain(root, rel)
    return rel, target


def resolve_under_repo(repo_root: Path, rel_path: str | Path) -> tuple[str, Path]:
    """
    Canonicalize rel_path under repo_root without creating directories.

    Missing targets are allowed as unresolved confined paths. Callers that
    require an existing file must use ``resolve_existing_under_repo``.
    """
    rel = normalize_repo_rel(rel_path)
    root = repo_root.resolve(strict=True)
    candidate = root / rel
    _assert_symlink_chain(root, rel)
    if candidate.exists() or candidate.is_symlink():
        target = candidate.resolve(strict=False)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise StopRequired(
                "PATH_ESCAPE_BLOCKED",
                {"path": rel, "resolved": str(target), "repo": str(root)},
            ) from exc
        return rel, target
    return rel, candidate
