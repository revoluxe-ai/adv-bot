"""Изолированный runtime evidence helper для COMPOSE child Jobs.

Модуль не запускает Kubernetes и не объединяет child payloads. Он создаёт
нормативный manifest, обновляет child gates, применяет required/optional
failure semantics и считает финальный digest внешним sidecar-файлом.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from collections.abc import Callable
from typing import Any, Mapping, Sequence

MANIFEST_SCHEMA = "opsx.compose-manifest.v1"
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "SKIPPED"}
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ARTIFACT_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ChildRunner = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _failure(code: str, message: str, retryable: bool) -> dict[str, Any]:
    """Сформировать exact failure object."""
    return {"code": code, "message": message, "retryable": retryable}


def create_manifest(
    run_id: str,
    execution_sha: str,
    registry_sha: str,
    children: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Создать RUNNING manifest до запуска первого child Job.

    Args:
        run_id: Уникальный run identity.
        execution_sha: Immutable canonical execution commit.
        registry_sha: 40-hex Git commit containing the Registry snapshot.
        children: Ordered resolver plan; each child must contain registry_id,
            collector_path, args and required.

    Returns:
        JSON-compatible manifest with no self-referential checksum.

    Raises:
        ValueError: если execution или Registry identity не являются
            lowercase 40-hex Git commit SHA.
    """
    if not GIT_SHA_PATTERN.fullmatch(execution_sha):
        raise ValueError("execution_sha must be a lowercase 40-hex Git SHA")
    if not GIT_SHA_PATTERN.fullmatch(registry_sha):
        raise ValueError("registry_sha must be a lowercase 40-hex Git SHA")
    normalized_children: list[dict[str, Any]] = []
    for order, child in enumerate(children, start=1):
        normalized_children.append(
            {
                "order": order,
                "registry_id": child["registry_id"],
                "required": bool(child["required"]),
                "collector_path": child["collector_path"],
                "job_name": None,
                "args": dict(child.get("args", {})),
                "execution_sha": execution_sha,
                "artifact_path": None,
                "sha256": None,
                "gate_status": "PENDING",
                "status": "PENDING",
                "failure": None,
            }
        )
    return {
        "schema_version": MANIFEST_SCHEMA,
        "run_id": run_id,
        "outcome": "COMPOSE",
        "status": "RUNNING",
        "execution_sha": execution_sha,
        "registry_sha": registry_sha,
        "children": normalized_children,
        "failure_details": [],
        "primary_artifact": {"path": "COMPOSE_MANIFEST.json", "accepted": False},
        "checksum_sidecar_path": "COMPOSE_MANIFEST.json.sha256",
        "external_handoff_ready": False,
    }


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    """Записать текущий manifest с deterministic JSON formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def record_child(
    manifest: dict[str, Any],
    order: int,
    *,
    job_name: str,
    status: str,
    gate_status: str,
    artifact_path: str | None,
    sha256: str | None,
    failure: Mapping[str, Any] | None = None,
) -> None:
    """Записать child gate и enforce terminal non-null/sentinel semantics."""
    child = next(item for item in manifest["children"] if item["order"] == order)
    if status not in TERMINAL_STATUSES:
        raise ValueError("record_child requires terminal child status")
    if gate_status not in {"PASS", "FAIL", "SKIPPED"}:
        raise ValueError("invalid terminal gate_status")
    if status == "SKIPPED":
        child.update(
            {
                "job_name": "NOT_CREATED",
                "artifact_path": "NOT_AVAILABLE",
                "sha256": "NOT_APPLICABLE",
                "gate_status": "SKIPPED",
                "status": "SKIPPED",
                "failure": dict(
                    failure
                    or _failure("CHILD_SKIPPED", "Child was not started.", False)
                ),
            }
        )
        return
    if failure is not None and set(failure) != {"code", "message", "retryable"}:
        raise ValueError("failure must contain exactly code, message, retryable")
    child.update(
        {
            "job_name": job_name,
            "artifact_path": artifact_path or "NOT_AVAILABLE",
            "sha256": sha256 or "NOT_AVAILABLE",
            "gate_status": gate_status,
            "status": status,
            "failure": dict(failure) if failure is not None else None,
        }
    )


def _manifest_digest(path: Path) -> str:
    """Посчитать SHA-256 finalized manifest bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_no_symlink_chain(path: Path) -> None:
    """Запретить symlink в artifact path и любом существующем родителе."""
    current = path
    while True:
        if current.is_symlink():
            raise ValueError(f"artifact path contains symlink: {current}")
        if current.parent == current:
            return
        current = current.parent


def _verify_artifact(
    manifest_path: Path, artifact_path: object, reported_sha256: object
) -> tuple[str, str]:
    """Проверить child artifact внутри manifest directory и вернуть verified SHA.

    Args:
        manifest_path: Путь к COMPOSE manifest; его directory является artifact
            root для child outputs.
        artifact_path: Путь, возвращённый child runner.
        reported_sha256: Digest, заявленный child runner.

    Returns:
        Нормализованный относительный artifact path и SHA-256 фактических bytes.

    Raises:
        ValueError: если путь unsafe, artifact отсутствует или digest mismatch.
    """
    if not isinstance(artifact_path, str) or not artifact_path:
        raise ValueError("mandatory child artifact path is missing")
    relative = Path(artifact_path)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError("child artifact path is outside the invocation artifact root")
    root = manifest_path.parent.resolve()
    target = root / relative
    _assert_no_symlink_chain(target)
    resolved_target = target.resolve(strict=False)
    try:
        resolved_target.relative_to(root)
    except ValueError as exc:
        raise ValueError("child artifact path escaped the invocation artifact root") from exc
    if not target.is_file():
        raise ValueError("mandatory child artifact is missing")
    actual_sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
    if not isinstance(reported_sha256, str) or not ARTIFACT_SHA256_PATTERN.fullmatch(
        reported_sha256
    ):
        raise ValueError("child artifact SHA-256 is missing or malformed")
    if reported_sha256 != actual_sha256:
        raise ValueError("child artifact SHA-256 mismatch")
    return relative.as_posix(), actual_sha256


def _verified_child_outcome(
    manifest_path: Path, outcome: Mapping[str, Any]
) -> dict[str, Any]:
    """Преобразовать child result в verified success либо gate failure."""
    normalized = dict(outcome)
    if normalized.get("status") != "SUCCEEDED" or normalized.get("gate_status") != "PASS":
        return normalized
    try:
        artifact_path, verified_sha256 = _verify_artifact(
            manifest_path,
            normalized.get("artifact_path"),
            normalized.get("sha256"),
        )
    except ValueError as exc:
        normalized.update(
            {
                "status": "FAILED",
                "gate_status": "FAIL",
                "artifact_path": None,
                "sha256": None,
                "failure": _failure("ARTIFACT_GATE", str(exc), False),
            }
        )
        return normalized
    normalized["artifact_path"] = artifact_path
    normalized["sha256"] = verified_sha256
    return normalized


def finalize_manifest(path: Path, manifest: dict[str, Any]) -> str:
    """Финализировать COMPOSE manifest и записать внешний checksum sidecar.

    Required child failure stops later required children; optional failures are
    retained and produce PARTIAL_FAILURE. No child payload is semantically
    merged by this function.

    Returns:
        Hex SHA-256 finalized `COMPOSE_MANIFEST.json`.
    """
    required_failure = False
    optional_failure = False
    for child in manifest["children"]:
        if child["status"] == "PENDING":
            if required_failure:
                record_child(
                    manifest,
                    int(child["order"]),
                    job_name="NOT_CREATED",
                    status="SKIPPED",
                    gate_status="SKIPPED",
                    artifact_path=None,
                    sha256=None,
                )
        if child["status"] == "FAILED":
            detail = dict(child["failure"] or _failure("CHILD_FAILED", "Child failed.", False))
            detail["child_order"] = child["order"]
            manifest["failure_details"].append(detail)
            if child["required"]:
                required_failure = True
            else:
                optional_failure = True
    if required_failure:
        manifest["status"] = "FAILED"
    elif optional_failure:
        manifest["status"] = "PARTIAL_FAILURE"
    else:
        manifest["status"] = "SUCCEEDED"
    accepted = manifest["status"] == "SUCCEEDED" and all(
        child["status"] == "SUCCEEDED" and child["gate_status"] == "PASS"
        for child in manifest["children"]
    )
    manifest["primary_artifact"]["accepted"] = accepted
    manifest["external_handoff_ready"] = accepted
    write_manifest(path, manifest)
    digest = _manifest_digest(path)
    sidecar = path.with_name(path.name + ".sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def execute_children(
    path: Path, manifest: dict[str, Any], run_child: ChildRunner
) -> tuple[dict[str, Any], str]:
    """Последовательно выполнить child runner через независимые artifact gates.

    `run_child` получает только один child plan row и должен вернуть
    `job_name`, `status`, `gate_status`, `artifact_path`, `sha256` и optional
    exact `failure`. Такой seam позволяет runtime adapter вызвать Kubernetes
    Job, не пряча orchestration semantics в Markdown command.

    Returns:
        Finalized manifest и внешний SHA-256 sidecar digest.
    """
    write_manifest(path, manifest)
    for child in manifest["children"]:
        if any(
            item["required"] and item["status"] == "FAILED"
            for item in manifest["children"]
        ):
            break
        outcome = _verified_child_outcome(path, run_child(child))
        record_child(
            manifest,
            int(child["order"]),
            job_name=str(outcome.get("job_name", "NOT_CREATED")),
            status=str(outcome["status"]),
            gate_status=str(outcome["gate_status"]),
            artifact_path=outcome.get("artifact_path"),
            sha256=outcome.get("sha256"),
            failure=outcome.get("failure"),
        )
        write_manifest(path, manifest)
    digest = finalize_manifest(path, manifest)
    return manifest, digest
