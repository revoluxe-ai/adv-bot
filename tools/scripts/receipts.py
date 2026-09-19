"""Машинные receipt writers для безопасной scripts resolution handoff.

Receipt path является invocation-owned evidence path, а не Registry или
collector write path. Модуль записывает только formal-change artifact и
передаёт provenance fields для SCRIPTS_REPORT.
"""

from __future__ import annotations

import json
import re
import stat
from pathlib import Path
from typing import Any, Mapping

FORMAL_SCHEMA = "opsx.formal-change-handoff.v1"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SAFE_COMPONENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_RECEIPT_SECRET_NAME = re.compile(
    r"(?i)(?:token|secret|password|api[_-]?key|authorization|cookie|credential)"
)
_RECEIPT_SECRET_VALUE = re.compile(
    r"(?i)^bearer\s+\S+$|^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"
)


def _sanitize_receipt_value(value: Any, field_name: str = "") -> Any:
    """Удалить credential material из persisted handoff evidence."""
    if _RECEIPT_SECRET_NAME.search(field_name) or (
        isinstance(value, str) and _RECEIPT_SECRET_VALUE.fullmatch(value.strip())
    ):
        return "<redacted>"
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_receipt_value(item, str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_receipt_value(item, field_name) for item in value]
    return value


def validate_run_id(run_id: str) -> str:
    """Проверить безопасный идентификатор invocation.

    Args:
        run_id: Идентификатор запуска, используемый в `.tmp` пути.

    Returns:
        Исходный идентификатор при успешной проверке.

    Raises:
        ValueError: если идентификатор пустой, содержит разделители,
            traversal или символы вне allowlist.
    """
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run_id must match the invocation allowlist")
    return run_id


def _is_link_or_reparse(path: Path) -> bool:
    """Проверить symlink или Windows reparse point без перехода по нему."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) & reparse_flag
    )


def _assert_no_link_chain(path: Path) -> None:
    """Запретить symlink/reparse escape по всей существующей цепочке."""
    current = path
    while True:
        if _is_link_or_reparse(current):
            raise ValueError(f"symlink/reparse path is forbidden: {current}")
        if current.parent == current:
            return
        current = current.parent


def invocation_root(caller_root: Path, run_id: str) -> Path:
    """Вычислить invocation-owned root строго под caller `.tmp`.

    Args:
        caller_root: Абсолютный корень caller worktree.
        run_id: Безопасный идентификатор запуска.

    Returns:
        Абсолютный путь `.tmp/opsx-scripts/<run_id>`, не создавая его.

    Raises:
        ValueError: если caller или run ID небезопасны.
    """
    if not caller_root.is_absolute():
        raise ValueError("caller_root must be absolute")
    validate_run_id(run_id)
    root = caller_root.resolve()
    if not root.is_dir():
        raise ValueError("caller_root must be an existing directory")
    target = root / ".tmp" / "opsx-scripts" / run_id
    _assert_no_link_chain(target)
    resolved_root = root.resolve()
    resolved_target = target.resolve(strict=False)
    try:
        if resolved_target.parent != (root / ".tmp" / "opsx-scripts").resolve(
            strict=False
        ):
            raise ValueError("invocation root escaped caller worktree")
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("invocation root escaped caller worktree") from exc
    return target


def invocation_output_path(
    caller_root: Path, run_id: str, component: str
) -> Path:
    """Вычислить безопасный child output path внутри invocation root.

    Args:
        caller_root: Абсолютный корень caller worktree.
        run_id: Безопасный идентификатор запуска.
        component: Один или несколько фиксированных безопасных path components.

    Returns:
        Абсолютный путь output component без создания каталога.

    Raises:
        ValueError: при traversal, абсолютном component или escape.
    """
    if not component or Path(component).is_absolute():
        raise ValueError("output component must be relative and non-empty")
    parts = Path(component).parts
    if any(
        part in {"", ".", ".."} or not _SAFE_COMPONENT_PATTERN.fullmatch(part)
        for part in parts
    ):
        raise ValueError("output component contains unsafe path parts")
    root = invocation_root(caller_root, run_id)
    target = root.joinpath(*parts)
    _assert_no_link_chain(target)
    try:
        target.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise ValueError("output path escaped invocation root") from exc
    return target


def prepare_invocation_output_dir(output_dir: Path) -> Path:
    """Создать новый invocation-owned output directory без удаления.

    Args:
        output_dir: Уже вычисленный абсолютный путь под
            `.tmp/opsx-scripts/<run_id>/`.

    Returns:
        Созданный абсолютный output directory.

    Raises:
        ValueError: если путь не соответствует invocation contract, содержит
            symlink/reparse escape или уже существует.
    """
    if not output_dir.is_absolute():
        raise ValueError("output_dir must be absolute")
    target = output_dir.resolve(strict=False)
    parts = target.parts
    marker = next(
        (
            index
            for index in range(len(parts) - 2)
            if parts[index].lower() == ".tmp"
            and parts[index + 1].lower() == "opsx-scripts"
        ),
        None,
    )
    if marker is None or marker + 2 >= len(parts):
        raise ValueError("output_dir must be under .tmp/opsx-scripts/<run_id>")
    validate_run_id(parts[marker + 2])
    _assert_no_link_chain(output_dir)
    invocation = Path(*parts[: marker + 3])
    try:
        target.relative_to(invocation.resolve(strict=False))
    except ValueError as exc:
        raise ValueError("output_dir escaped invocation root") from exc
    if output_dir.exists() or _is_link_or_reparse(output_dir):
        raise ValueError("output directory collision")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir()
    return output_dir.resolve()


def persist_formal_change(
    caller_root: Path, run_id: str, formal_change: Mapping[str, Any]
) -> Path:
    """Сохранить единственный formal-change handoff artifact.

    Args:
        caller_root: Абсолютный caller worktree, где живёт invocation receipt.
        run_id: Resolver run identity.
        formal_change: `formal_change` object из resolver result.

    Returns:
        Абсолютный путь `.tmp/opsx-scripts/<run_id>/FORMAL_CHANGE_REQUIRED.json`.

    Raises:
        ValueError: если outcome/schema или обязательные поля нарушены.
    """
    if not caller_root.is_absolute():
        raise ValueError("caller_root must be absolute")
    if formal_change.get("schema_version") != FORMAL_SCHEMA:
        raise ValueError("formal change schema mismatch")
    required = {
        "schema_version",
        "outcome",
        "run_id",
        "request_id",
        "formal_type",
        "command",
        "change_name",
        "owner_change_id",
        "reason",
        "evidence",
        "request_contract",
        "constraints",
        "pasteable_prompt",
        "created_at",
    }
    if set(formal_change) != required:
        raise ValueError("formal change artifact keys mismatch")
    if formal_change.get("outcome") != "FORMAL_CHANGE_REQUIRED":
        raise ValueError("formal change outcome mismatch")
    if formal_change.get("run_id") != run_id:
        raise ValueError("formal change run_id mismatch")
    run_root = invocation_root(caller_root.resolve(), run_id)
    if run_root.exists() or _is_link_or_reparse(run_root):
        raise ValueError("invocation receipt collision")
    _assert_no_link_chain(run_root)
    run_root.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir()
    destination = run_root / "FORMAL_CHANGE_REQUIRED.json"
    safe_formal_change = _sanitize_receipt_value(dict(formal_change))
    destination.write_text(
        json.dumps(safe_formal_change, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def scripts_report_provenance(result: Mapping[str, Any]) -> dict[str, str]:
    """Построить additive provenance fields для `SCRIPTS_REPORT`."""
    caller = result.get("caller") or {}
    canonical = result.get("canonical_worktree") or {}
    return {
        "CALLER_BRANCH": str(caller.get("branch", "NONE")),
        "CALLER_WORKTREE": str(caller.get("root", "NONE")),
        "CALLER_SHA": str(caller.get("sha", "NONE")),
        "EXECUTION_SHA": str(result.get("execution_sha") or "NONE"),
        "REGISTRY_SHA": str(result.get("registry_sha") or "NONE"),
        "RESOLUTION_OUTCOME": str(result.get("outcome") or "BLOCKED"),
        "RESOLUTION_PLAN": json.dumps(
            result.get("compose_plan") or result.get("selection") or [],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "CANONICAL_WORKTREE": str(canonical.get("root", "NONE")),
    }
