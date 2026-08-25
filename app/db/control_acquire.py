"""
CONTROL Job: provenance-bound verify_baseline_and_acquire_release.

Не исполняет RELEASE image. Provenance — OCI digest pin / registry fetch
(``app.db.provenance``). Acquire — SECURITY DEFINER SQL в migration_control.

Env (обязательные):
  RELEASE_ID, RELEASE_PLATFORM_MANIFEST_DIGEST, DATABASE_URL,
  EXPECTED_TARGET_REVISION, EXPECTED_SOURCE_HISTORY_HASH,
  WORKFLOW_RUN_ID, DATABASE_IDENTITY

Опциональные:
  TARGET_PLATFORM (default linux/amd64),
  PROVENANCE_MODE (digest_pin|registry_manifest),
  EXPECTED_PLATFORM_MANIFEST_DIGEST, RELEASE_INDEX_DIGEST,
  REGISTRY_HOST, REGISTRY_REPOSITORY, REGISTRY_USER, REGISTRY_PASSWORD,
  SOURCE_REVISION_SET (JSON array), LEASE_TTL_SECONDS (default 3600),
  CONTROL_DRY_RUN=1 — provenance + SELECT baseline, без acquire.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, cast

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.db.provenance import ProvenanceError, verify_release_platform_digest


class ControlOutcome(str, Enum):
    """Коды исхода CONTROL Job."""

    ACQUIRED = "ACQUIRED"
    IDEMPOTENT_HIT = "IDEMPOTENT_HIT"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    PROVENANCE_FAILED = "PROVENANCE_FAILED"
    DRY_RUN_OK = "DRY_RUN_OK"


def _emit(payload: dict[str, Any], *, exit_code: int) -> int:
    """Печатает JSON outcome и возвращает process exit code."""
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return exit_code


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"missing required env: {name}")
    return value


def _source_revision_set() -> list[str]:
    raw = os.environ.get("SOURCE_REVISION_SET", "").strip()
    if not raw:
        # Default: singleton set of expected target (Expand-compatible acquire).
        return [_require("EXPECTED_TARGET_REVISION")]
    data_obj = json.loads(raw)
    if not isinstance(data_obj, list) or not data_obj:
        raise ValueError("SOURCE_REVISION_SET must be a non-empty JSON array")
    data = cast(list[object], data_obj)
    return [str(x) for x in data]


def _lease_expires_at() -> datetime:
    ttl = int(os.environ.get("LEASE_TTL_SECONDS", "3600").strip() or "3600")
    if ttl < 60 or ttl > 86_400:
        raise ValueError("LEASE_TTL_SECONDS must be in [60, 86400]")
    return datetime.now(timezone.utc) + timedelta(seconds=ttl)


def _run_provenance() -> dict[str, Any]:
    result = verify_release_platform_digest(
        platform_manifest_digest=_require("RELEASE_PLATFORM_MANIFEST_DIGEST"),
        platform=os.environ.get("TARGET_PLATFORM", "linux/amd64"),
        mode=os.environ.get("PROVENANCE_MODE", "digest_pin"),
        expected_platform_manifest_digest=os.environ.get(
            "EXPECTED_PLATFORM_MANIFEST_DIGEST", ""
        ),
        index_digest=os.environ.get("RELEASE_INDEX_DIGEST", ""),
        registry_host=os.environ.get("REGISTRY_HOST", ""),
        repository=os.environ.get("REGISTRY_REPOSITORY", ""),
        username=os.environ.get("REGISTRY_USER", ""),
        password=os.environ.get("REGISTRY_PASSWORD", ""),
    )
    return {
        "mode": result.mode,
        "platform": result.platform,
        "platform_manifest_digest": result.platform_manifest_digest,
        "index_digest": result.index_digest,
        "registry_checked": result.registry_checked,
        "detail": result.detail,
    }


def _dry_run_baseline(engine: Any, *, database_identity: str, source_history_hash: str) -> None:
    """SELECT-only проверка APPLICATION baseline (без acquire)."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT baseline_id, status, source_history_hash
                FROM migration_control.baseline_registry
                WHERE database_identity = :identity
                  AND schema_scope = 'APPLICATION'
                  AND status = 'RECONCILED'
                """
            ),
            {"identity": database_identity},
        ).mappings().first()
        if row is None:
            raise RuntimeError(
                "BASELINE_PRECONDITION_FAILED: no RECONCILED APPLICATION baseline"
            )
        if str(row["source_history_hash"]) != source_history_hash:
            raise RuntimeError(
                "BASELINE_PRECONDITION_FAILED: source_history_hash mismatch"
            )


def _acquire(
    engine: Any,
    *,
    release_id: str,
    workflow_run_id: str,
    image_digest: str,
    source_revision_set: list[str],
    target_revision: str,
    lease_expires_at: datetime,
    database_identity: str,
    source_history_hash: str,
) -> dict[str, Any]:
    """Вызывает verify_baseline_and_acquire_release."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT migration_control.verify_baseline_and_acquire_release(
                    :release_id,
                    :workflow_run_id,
                    :image_digest,
                    CAST(:source_revision_set AS jsonb),
                    :target_revision,
                    :lease_expires_at,
                    :database_identity,
                    :source_history_hash
                ) AS result
                """
            ),
            {
                "release_id": release_id,
                "workflow_run_id": workflow_run_id,
                "image_digest": image_digest,
                "source_revision_set": json.dumps(source_revision_set),
                "target_revision": target_revision,
                "lease_expires_at": lease_expires_at,
                "database_identity": database_identity,
                "source_history_hash": source_history_hash,
            },
        ).mappings().one()
        result_obj = row["result"]
        if isinstance(result_obj, str):
            result_obj = json.loads(result_obj)
        if not isinstance(result_obj, dict):
            raise RuntimeError(f"unexpected acquire result type: {type(result_obj)}")
        result = cast(dict[str, Any], result_obj)
        return result


def main() -> int:
    """Entrypoint CONTROL acquire; никогда не exec RELEASE."""
    release_id = os.environ.get("RELEASE_ID", "").strip()
    base: dict[str, Any] = {
        "release_id": release_id,
        "target_platform": os.environ.get("TARGET_PLATFORM", "linux/amd64"),
    }
    try:
        missing = [
            k
            for k in (
                "RELEASE_ID",
                "RELEASE_PLATFORM_MANIFEST_DIGEST",
                "DATABASE_URL",
                "EXPECTED_TARGET_REVISION",
                "EXPECTED_SOURCE_HISTORY_HASH",
                "WORKFLOW_RUN_ID",
                "DATABASE_IDENTITY",
            )
            if not os.environ.get(k, "").strip()
        ]
        if missing:
            return _emit(
                {
                    **base,
                    "outcome": ControlOutcome.PRECONDITION_FAILED.value,
                    "detail": "missing required env",
                    "missing_env": missing,
                },
                exit_code=2,
            )

        provenance = _run_provenance()
        database_url = _require("DATABASE_URL")
        source_history_hash = _require("EXPECTED_SOURCE_HISTORY_HASH")
        database_identity = _require("DATABASE_IDENTITY")
        dry_run = os.environ.get("CONTROL_DRY_RUN", "").strip() == "1"
        engine = create_engine(database_url, poolclass=NullPool, pool_pre_ping=True)
        try:
            if dry_run:
                _dry_run_baseline(
                    engine,
                    database_identity=database_identity,
                    source_history_hash=source_history_hash,
                )
                return _emit(
                    {
                        **base,
                        "outcome": ControlOutcome.DRY_RUN_OK.value,
                        "detail": "provenance OK; APPLICATION baseline matches; acquire skipped",
                        "provenance": provenance,
                        "source_history_hash": source_history_hash,
                        "database_identity": database_identity,
                    },
                    exit_code=0,
                )

            acquire_result = _acquire(
                engine,
                release_id=_require("RELEASE_ID"),
                workflow_run_id=_require("WORKFLOW_RUN_ID"),
                image_digest=provenance["platform_manifest_digest"],
                source_revision_set=_source_revision_set(),
                target_revision=_require("EXPECTED_TARGET_REVISION"),
                lease_expires_at=_lease_expires_at(),
                database_identity=database_identity,
                source_history_hash=source_history_hash,
            )
        finally:
            engine.dispose()

        status = str(acquire_result.get("status", ""))
        if status == "ACQUIRED":
            outcome = ControlOutcome.ACQUIRED
        elif status == "IDEMPOTENT_HIT":
            outcome = ControlOutcome.IDEMPOTENT_HIT
        else:
            return _emit(
                {
                    **base,
                    "outcome": ControlOutcome.PRECONDITION_FAILED.value,
                    "detail": f"unexpected acquire status: {status}",
                    "provenance": provenance,
                    "acquire": acquire_result,
                },
                exit_code=2,
            )
        return _emit(
            {
                **base,
                "outcome": outcome.value,
                "detail": "verify_baseline_and_acquire_release OK",
                "provenance": provenance,
                "acquire": acquire_result,
                "fencing_token": acquire_result.get("fencing_token"),
            },
            exit_code=0,
        )
    except ProvenanceError as exc:
        return _emit(
            {
                **base,
                "outcome": ControlOutcome.PROVENANCE_FAILED.value,
                "detail": str(exc),
            },
            exit_code=3,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        return _emit(
            {
                **base,
                "outcome": ControlOutcome.PRECONDITION_FAILED.value,
                "detail": str(exc),
            },
            exit_code=2,
        )
    except SQLAlchemyError as exc:
        return _emit(
            {
                **base,
                "outcome": ControlOutcome.PRECONDITION_FAILED.value,
                "detail": f"database error: {exc}",
            },
            exit_code=2,
        )
    except RuntimeError as exc:
        return _emit(
            {
                **base,
                "outcome": ControlOutcome.PRECONDITION_FAILED.value,
                "detail": str(exc),
            },
            exit_code=2,
        )


if __name__ == "__main__":
    sys.exit(main())