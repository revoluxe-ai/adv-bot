"""Unit tests for COMPOSE manifest lifecycle and external checksum gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.scripts import compose_runtime

pytestmark = pytest.mark.unit


def _children() -> list[dict[str, object]]:
    """Создать ordered child plan fixture для manifest tests."""
    return [
        {
            "registry_id": "first",
            "collector_path": "scripts/first.py",
            "args": {"shop_id": "shop"},
            "required": True,
        },
        {
            "registry_id": "optional",
            "collector_path": "scripts/optional.py",
            "args": {},
            "required": False,
        },
    ]


def _five_children() -> list[dict[str, object]]:
    """Создать пятиэлементный ordered child plan для manifest evidence."""
    return [
        {
            "registry_id": f"child-{index}",
            "collector_path": f"scripts/child_{index}.py",
            "args": {"order": index},
            "required": True,
        }
        for index in range(1, 6)
    ]


def _write_artifact(path: Path, relative: str, content: bytes) -> str:
    """Создать fixture artifact и вернуть digest фактических bytes."""
    artifact = path.parent / relative
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def test_running_manifest_has_exact_nullability_and_no_self_hash() -> None:
    """RUNNING child evidence is nullable and manifest has no own SHA field."""
    manifest = compose_runtime.create_manifest("run-1", "a" * 40, "b" * 40, _children())
    assert manifest["status"] == "RUNNING"
    assert manifest["primary_artifact"] == {
        "path": "COMPOSE_MANIFEST.json",
        "accepted": False,
    }
    assert "sha256" not in manifest
    assert all(child["job_name"] is None for child in manifest["children"])


def test_required_failure_skips_remaining_children_and_rejects_handoff(
    tmp_path: Path,
) -> None:
    """Required child failure produces sentinels and external handoff NO."""
    manifest = compose_runtime.create_manifest("run-2", "a" * 40, "b" * 40, _children())
    compose_runtime.record_child(
        manifest,
        1,
        job_name="job-first",
        status="FAILED",
        gate_status="FAIL",
        artifact_path=None,
        sha256=None,
        failure={"code": "CHECKSUM", "message": "bad digest", "retryable": False},
    )
    path = tmp_path / "COMPOSE_MANIFEST.json"
    digest = compose_runtime.finalize_manifest(path, manifest)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["status"] == "FAILED"
    assert written["external_handoff_ready"] is False
    assert written["children"][1]["job_name"] == "NOT_CREATED"
    assert written["children"][1]["artifact_path"] == "NOT_AVAILABLE"
    assert written["children"][1]["sha256"] == "NOT_APPLICABLE"
    assert "sha256" not in written
    assert (tmp_path / "COMPOSE_MANIFEST.json.sha256").read_text(
        encoding="utf-8"
    ).startswith(digest)


def test_optional_failure_continues_but_manifest_is_partial(tmp_path: Path) -> None:
    """Optional child failure is recorded without accepting composite handoff."""
    manifest = compose_runtime.create_manifest("run-3", "a" * 40, "b" * 40, _children())
    compose_runtime.record_child(
        manifest,
        1,
        job_name="job-first",
        status="SUCCEEDED",
        gate_status="PASS",
        artifact_path="first.zip",
        sha256="c" * 64,
    )
    compose_runtime.record_child(
        manifest,
        2,
        job_name="job-optional",
        status="FAILED",
        gate_status="FAIL",
        artifact_path=None,
        sha256=None,
        failure={"code": "JOB", "message": "optional failed", "retryable": True},
    )
    path = tmp_path / "COMPOSE_MANIFEST.json"
    compose_runtime.finalize_manifest(path, manifest)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["status"] == "PARTIAL_FAILURE"
    assert written["external_handoff_ready"] is False
    assert written["primary_artifact"]["accepted"] is False


def test_execute_children_is_sequential_and_does_not_merge_payloads(
    tmp_path: Path,
) -> None:
    """Runtime seam invokes child jobs in order and writes only evidence."""
    manifest = compose_runtime.create_manifest("run-4", "a" * 40, "b" * 40, _children())
    observed: list[str] = []
    path = tmp_path / "COMPOSE_MANIFEST.json"

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Вернуть independent child gate result для orchestration seam."""
        observed.append(str(child["registry_id"]))
        artifact_path = f"{child['registry_id']}.zip"
        return {
            "job_name": f"job-{child['registry_id']}",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": artifact_path,
            "sha256": _write_artifact(path, artifact_path, b"verified-child"),
        }

    final, digest = compose_runtime.execute_children(path, manifest, run_child)
    assert observed == ["first", "optional"]
    assert final["status"] == "SUCCEEDED"
    assert final["external_handoff_ready"] is True
    assert digest
    assert "merged_payload" not in final


def test_missing_mandatory_artifact_fails_child_gate(tmp_path: Path) -> None:
    """Отсутствующий mandatory artifact не может считаться успешным child."""
    manifest = compose_runtime.create_manifest("run-missing", "a" * 40, "b" * 40, _children())
    path = tmp_path / "COMPOSE_MANIFEST.json"

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Вернуть success claim без создания artifact."""
        return {
            "job_name": "job-missing",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": "missing.zip",
            "sha256": "0" * 64,
        }

    final, _ = compose_runtime.execute_children(path, manifest, run_child)

    assert final["status"] == "FAILED"
    assert final["children"][0]["status"] == "FAILED"
    assert final["children"][0]["failure"]["code"] == "ARTIFACT_GATE"
    assert final["external_handoff_ready"] is False


def test_incorrect_reported_sha_fails_child_gate(tmp_path: Path) -> None:
    """Неверный digest child runner отклоняется по фактическим bytes."""
    manifest = compose_runtime.create_manifest("run-mismatch", "a" * 40, "b" * 40, _children())
    path = tmp_path / "COMPOSE_MANIFEST.json"

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Создать artifact и вернуть заведомо неверный digest."""
        _write_artifact(path, "first.zip", b"actual")
        return {
            "job_name": "job-mismatch",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": "first.zip",
            "sha256": "0" * 64,
        }

    final, _ = compose_runtime.execute_children(path, manifest, run_child)

    assert final["children"][0]["status"] == "FAILED"
    assert final["children"][0]["failure"]["code"] == "ARTIFACT_GATE"
    assert final["external_handoff_ready"] is False


def test_artifact_modified_after_claimed_digest_fails_gate(tmp_path: Path) -> None:
    """Изменение artifact после claimed digest выявляется чтением runtime."""
    manifest = compose_runtime.create_manifest("run-modified", "a" * 40, "b" * 40, _children())
    path = tmp_path / "COMPOSE_MANIFEST.json"

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Сначала получить digest, затем изменить фактический artifact."""
        artifact = path.parent / "first.zip"
        artifact.write_bytes(b"before")
        claimed = hashlib.sha256(b"before").hexdigest()
        artifact.write_bytes(b"after")
        return {
            "job_name": "job-modified",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": "first.zip",
            "sha256": claimed,
        }

    final, _ = compose_runtime.execute_children(path, manifest, run_child)

    assert final["children"][0]["status"] == "FAILED"
    assert final["children"][0]["failure"]["code"] == "ARTIFACT_GATE"
    assert final["external_handoff_ready"] is False


def test_verified_digest_is_written_to_manifest(tmp_path: Path) -> None:
    """Manifest stores digest recomputed from the accepted artifact bytes."""
    manifest = compose_runtime.create_manifest("run-verified", "a" * 40, "b" * 40, _children())
    path = tmp_path / "COMPOSE_MANIFEST.json"
    content = b"verified-content"
    expected = hashlib.sha256(content).hexdigest()

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Создать artifact с matching reported digest."""
        return {
            "job_name": "job-verified",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": "first.zip",
            "sha256": _write_artifact(path, "first.zip", content),
        }

    final, _ = compose_runtime.execute_children(path, manifest, run_child)

    assert final["children"][0]["status"] == "SUCCEEDED"
    assert final["children"][0]["sha256"] == expected
    assert final["external_handoff_ready"] is True


def test_registry_sha_is_exact_git_commit_identity() -> None:
    """Manifest preserves a lowercase Git commit SHA, not content digest."""
    registry_sha = "b" * 40
    manifest = compose_runtime.create_manifest(
        "run-sha",
        "a" * 40,
        registry_sha,
        _children(),
    )
    assert manifest["registry_sha"] == registry_sha
    with pytest.raises(ValueError, match="registry_sha"):
        compose_runtime.create_manifest("run-invalid", "a" * 40, "b" * 64, _children())


def test_manifest_is_written_before_and_after_each_child_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Manifest snapshots prove start-before-run and per-gate persistence."""
    manifest = compose_runtime.create_manifest("run-lifecycle", "a" * 40, "b" * 40, _children())
    path = tmp_path / "COMPOSE_MANIFEST.json"
    snapshots: list[dict[str, object]] = []
    original_write = compose_runtime.write_manifest

    def capture(path: Path, current: dict[str, object]) -> None:
        snapshots.append(json.loads(json.dumps(current)))
        original_write(path, current)

    monkeypatch.setattr(compose_runtime, "write_manifest", capture)

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Return a successful independent child gate."""
        artifact_path = f"{child['registry_id']}.zip"
        return {
            "job_name": f"job-{child['registry_id']}",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": artifact_path,
            "sha256": _write_artifact(path, artifact_path, b"lifecycle-child"),
        }

    compose_runtime.execute_children(
        path,
        manifest,
        run_child,
    )

    assert snapshots[0]["status"] == "RUNNING"
    assert snapshots[0]["children"][0]["status"] == "PENDING"
    assert snapshots[1]["children"][0]["status"] == "SUCCEEDED"
    assert snapshots[2]["children"][1]["status"] == "SUCCEEDED"


def test_five_child_manifest_records_evidence_for_each_child(
    tmp_path: Path,
) -> None:
    """Unbounded valid plans persist terminal evidence for every child."""
    manifest = compose_runtime.create_manifest(
        "run-five",
        "a" * 40,
        "b" * 40,
        _five_children(),
    )
    path = tmp_path / "COMPOSE_MANIFEST.json"

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Return a successful gate with child-specific evidence."""
        registry_id = str(child["registry_id"])
        artifact_path = f"{registry_id}.zip"
        return {
            "job_name": f"job-{registry_id}",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": artifact_path,
            "sha256": _write_artifact(path, artifact_path, registry_id.encode()),
        }

    final, digest = compose_runtime.execute_children(path, manifest, run_child)

    assert final["status"] == "SUCCEEDED"
    assert final["external_handoff_ready"] is True
    assert len(final["children"]) == 5
    assert all(
        child["job_name"]
        and child["artifact_path"]
        and child["sha256"]
        and child["gate_status"] == "PASS"
        for child in final["children"]
    )
    assert path.with_suffix(path.suffix + ".sha256").is_file()
    assert digest


def test_manifest_preserves_partial_state_before_failure_finalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed required child is persisted before terminal finalization."""
    manifest = compose_runtime.create_manifest("run-failure", "a" * 40, "b" * 40, _children())
    snapshots: list[dict[str, object]] = []
    original_write = compose_runtime.write_manifest

    def capture(path: Path, current: dict[str, object]) -> None:
        snapshots.append(json.loads(json.dumps(current)))
        original_write(path, current)

    monkeypatch.setattr(compose_runtime, "write_manifest", capture)

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Return a required child gate failure."""
        return {
            "job_name": "job-first",
            "status": "FAILED",
            "gate_status": "FAIL",
            "artifact_path": None,
            "sha256": None,
            "failure": {
                "code": "CHECKSUM",
                "message": "bad digest",
                "retryable": False,
            },
        }

    path = tmp_path / "COMPOSE_MANIFEST.json"
    final, digest = compose_runtime.execute_children(path, manifest, run_child)

    assert snapshots[0]["status"] == "RUNNING"
    assert snapshots[1]["children"][0]["status"] == "FAILED"
    assert final["status"] == "FAILED"
    assert final["children"][1]["status"] == "SKIPPED"
    assert path.with_suffix(path.suffix + ".sha256").is_file()
    assert digest


def test_required_failure_retains_prior_verified_partial_artifact(tmp_path: Path) -> None:
    """Mandatory failure сохраняет уже прошедший child artifact."""
    children = _children()
    children[1]["required"] = True
    manifest = compose_runtime.create_manifest(
        "run-partial-verified", "a" * 40, "b" * 40, children
    )
    path = tmp_path / "COMPOSE_MANIFEST.json"
    calls = 0

    def run_child(child: dict[str, object]) -> dict[str, object]:
        """Успешно завершить первый child и сломать mandatory второй."""
        nonlocal calls
        calls += 1
        if calls == 1:
            artifact_path = "first.zip"
            return {
                "job_name": "job-first",
                "status": "SUCCEEDED",
                "gate_status": "PASS",
                "artifact_path": artifact_path,
                "sha256": _write_artifact(path, artifact_path, b"first"),
            }
        return {
            "job_name": "job-optional",
            "status": "SUCCEEDED",
            "gate_status": "PASS",
            "artifact_path": "missing.zip",
            "sha256": "0" * 64,
        }

    final, _ = compose_runtime.execute_children(path, manifest, run_child)

    assert final["status"] == "FAILED"
    assert final["children"][0]["status"] == "SUCCEEDED"
    assert final["children"][0]["sha256"] == hashlib.sha256(b"first").hexdigest()
    assert final["children"][1]["status"] == "FAILED"
    assert final["external_handoff_ready"] is False


def test_parallel_compose_runs_keep_manifests_jobs_and_checksums_isolated(
    tmp_path: Path,
) -> None:
    """Two concurrent runs never overwrite each other's evidence."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)

    def execute(run_id: str, checksum: str) -> tuple[Path, dict[str, object], str]:
        """Execute one isolated parent/child manifest."""
        path = tmp_path / run_id / "COMPOSE_MANIFEST.json"
        manifest = compose_runtime.create_manifest(
            run_id,
            "a" * 40,
            "b" * 40,
            _children(),
        )

        def run_child(child: dict[str, object]) -> dict[str, object]:
            """Synchronize same-order children from separate runs."""
            barrier.wait()
            artifact_path = f"{child['registry_id']}.zip"
            return {
                "job_name": f"{run_id}-{child['registry_id']}",
                "status": "SUCCEEDED",
                "gate_status": "PASS",
                "artifact_path": artifact_path,
                "sha256": _write_artifact(path, artifact_path, run_id.encode()),
            }

        final, digest = compose_runtime.execute_children(path, manifest, run_child)
        return path, final, digest

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(execute, "run-a", "a" * 64)
        second_future = executor.submit(execute, "run-b", "b" * 64)
        first_path, first, first_digest = first_future.result()
        second_path, second, second_digest = second_future.result()

    assert first_path != second_path
    assert first_path.with_suffix(first_path.suffix + ".sha256") != second_path.with_suffix(
        second_path.suffix + ".sha256"
    )
    assert first["children"][0]["job_name"].startswith("run-a-")
    assert second["children"][0]["job_name"].startswith("run-b-")
    assert first["children"][0]["sha256"] != second["children"][0]["sha256"]
    assert first_digest != second_digest
    assert first_path.read_bytes() != second_path.read_bytes()
