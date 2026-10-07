"""Fail-closed guard for authorized scenario provider pytest runs.

Проверяет INDEPENDENT_REAUDIT packet и audited-state fingerprints до любого
``subprocess``/pytest. Несовпадение → ``BLOCKED_FINGERPRINT_MISMATCH``, spawn 0.

Канонические git-команды: ``/opsx-close-external-gap`` (B2 audited-state).
Хеш frozen run block: SHA-256 от UTF-8 текста блока; если байты не оканчиваются
на ``\\n``, добавляется один trailing LF (как при публикации в ```bash fence).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

EXIT_BLOCKED_FINGERPRINT = 3
EXIT_PERMIT = 0
EXIT_USAGE = 2

GuardStatus = Literal[
    "PERMIT",
    "BLOCKED_FINGERPRINT_MISMATCH",
    "BLOCKED_AUTHORIZATION",
    "BLOCKED_PACKET_INVALID",
]

AuthorizationState = Literal[
    "NOT_AUTHORIZED",
    "AUTHORIZED_UNUSED",
    "AUTHORIZED_CONSUMED",
    "EXPIRED_OR_INVALID",
]

EXIT_BLOCKED_AUTHORIZATION = 4


@dataclass(frozen=True)
class ProviderRunPacket:
    """Ожидаемые поля из INDEPENDENT_REAUDIT + frozen run block."""

    audited_head: str
    audited_status_sha256: str
    audited_tracked_diff_sha256: str
    audited_untracked_manifest_sha256: str
    allowed_run_block_sha256: str
    allowed_run_block_text: str
    pytest_argv: tuple[str, ...]
    provider_test_ids: tuple[str, ...]
    postgres_host: str
    postgres_port: int
    postgres_dbname: str
    change_id: str
    one_shot_authorization_id: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ProviderRunPacket:
        """Собрать packet из JSON/dict; KeyError → BLOCKED_PACKET_INVALID."""

        def _req(key: str) -> Any:
            if key not in data:
                raise KeyError(key)
            return data[key]

        pytest_raw = _req("pytest_argv")
        if isinstance(pytest_raw, str):
            pytest_argv = tuple(pytest_raw.split())
        else:
            pytest_argv = tuple(str(x) for x in pytest_raw)

        test_ids_raw = _req("provider_test_ids")
        provider_test_ids = tuple(str(x) for x in test_ids_raw)

        port_raw = _req("postgres_port")
        postgres_port = int(port_raw)

        return cls(
            audited_head=str(_req("audited_head")),
            audited_status_sha256=str(_req("audited_status_sha256")),
            audited_tracked_diff_sha256=str(_req("audited_tracked_diff_sha256")),
            audited_untracked_manifest_sha256=str(
                _req("audited_untracked_manifest_sha256")
            ),
            allowed_run_block_sha256=str(_req("allowed_run_block_sha256")),
            allowed_run_block_text=str(_req("allowed_run_block_text")),
            pytest_argv=pytest_argv,
            provider_test_ids=provider_test_ids,
            postgres_host=str(_req("postgres_host")),
            postgres_port=postgres_port,
            postgres_dbname=str(_req("postgres_dbname")),
            change_id=str(_req("change_id")),
            one_shot_authorization_id=str(_req("one_shot_authorization_id")),
        )


@dataclass(frozen=True)
class GuardVerdict:
    """Результат проверки до spawn."""

    status: GuardStatus
    mismatch_field: str | None = None
    expected: str | None = None
    computed: str | None = None
    spawn_count: int = 0
    authorization_state: AuthorizationState | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_bytes(payload: bytes) -> str:
    """SHA-256 lowercase hex от точных байт stdout/блока."""

    return hashlib.sha256(payload).hexdigest()


def allowed_run_block_sha256(block_text: str) -> str:
    """Хеш опубликованного frozen shell block (см. module docstring)."""

    payload = block_text.encode("utf-8")
    if not payload.endswith(b"\n"):
        payload = payload + b"\n"
    return sha256_bytes(payload)


def extract_bash_fence(markdown_text: str) -> str:
    """Извлечь первый ```bash fenced block из markdown."""

    marker = "```bash\n"
    start = markdown_text.find(marker)
    if start < 0:
        raise ValueError("bash_fence_missing")
    start += len(marker)
    end = markdown_text.find("\n```", start)
    if end < 0:
        raise ValueError("bash_fence_unclosed")
    return markdown_text[start:end]


def load_allowed_run_block_from_markdown(path: Path) -> str:
    """Прочитать frozen block из independent re-audit markdown."""

    return extract_bash_fence(path.read_text(encoding="utf-8"))


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git_failed:{args!r}:rc={result.returncode}")
    return result.stdout


def compute_audited_head(repo_root: Path) -> str:
    """``git rev-parse HEAD`` (trimmed)."""

    return _git_bytes(repo_root, "rev-parse", "HEAD").decode("utf-8").strip()


def compute_audited_status_sha256(repo_root: Path) -> str:
    """B2: porcelain status -z → SHA-256 stdout bytes."""

    stdout = _git_bytes(
        repo_root,
        "-c",
        "color.ui=false",
        "-c",
        "core.quotepath=false",
        "status",
        "--porcelain=v1",
        "-z",
    )
    return sha256_bytes(stdout)


def compute_audited_tracked_diff_sha256(repo_root: Path) -> str:
    """B2: tracked diff against HEAD → SHA-256 stdout bytes."""

    stdout = _git_bytes(
        repo_root,
        "-c",
        "color.ui=false",
        "-c",
        "core.quotepath=false",
        "diff",
        "--binary",
        "--full-index",
        "--no-ext-diff",
        "--no-textconv",
        "HEAD",
        "--",
    )
    return sha256_bytes(stdout)


def compute_audited_untracked_manifest_sha256(repo_root: Path) -> str:
    """B2: sorted untracked manifest records → SHA-256."""

    raw_paths = _git_bytes(
        repo_root, "ls-files", "--others", "--exclude-standard", "-z"
    )
    paths = sorted(
        p.decode("utf-8")
        for p in raw_paths.split(b"\0")
        if p
    )
    records = bytearray()
    for rel in paths:
        file_path = repo_root / rel
        if not file_path.is_file():
            raise RuntimeError(f"NON_REGULAR_UNTRACKED:{rel}")
        content = file_path.read_bytes()
        line = (
            f"{rel}\t{len(content)}\t{hashlib.sha256(content).hexdigest()}\n"
        )
        records.extend(line.encode("utf-8"))
    return sha256_bytes(bytes(records))


def _blocked(
    mismatch_field: str,
    expected: str,
    computed: str,
) -> GuardVerdict:
    return GuardVerdict(
        status="BLOCKED_FINGERPRINT_MISMATCH",
        mismatch_field=mismatch_field,
        expected=expected,
        computed=computed,
        spawn_count=0,
    )


def one_shot_authorization_token_sha256(token: str) -> str:
    """SHA-256 fingerprint of ``AUTHORIZE_ONE_LIVE_RUN`` secret (UTF-8)."""

    return sha256_bytes(token.encode("utf-8"))


def authorization_ledger_path(repo_root: Path, change_id: str) -> Path:
    """Durable one-shot consumption ledger (not certification evidence)."""

    return (
        repo_root
        / ".opsx"
        / "runs"
        / "scenario-coverage"
        / change_id
        / "one_shot_authorization.json"
    )


def _load_authorization_ledger(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_authorization_ledger(
    path: Path,
    *,
    one_shot_authorization_id: str,
    authorization_state: AuthorizationState,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "one_shot_authorization_id": one_shot_authorization_id,
        "authorization_state": authorization_state,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_authorization_state(
    repo_root: Path,
    packet: ProviderRunPacket,
    *,
    live_token: str | None,
) -> AuthorizationState:
    """Classify authorization without consuming the one-shot token."""

    if not live_token:
        return "NOT_AUTHORIZED"
    token_id = one_shot_authorization_token_sha256(live_token)
    if token_id != packet.one_shot_authorization_id:
        return "EXPIRED_OR_INVALID"
    ledger_path = authorization_ledger_path(repo_root, packet.change_id)
    ledger = _load_authorization_ledger(ledger_path)
    if ledger is None:
        return "AUTHORIZED_UNUSED"
    stored_id = str(ledger.get("one_shot_authorization_id", ""))
    stored_state = str(ledger.get("authorization_state", ""))
    if stored_id != packet.one_shot_authorization_id:
        return "EXPIRED_OR_INVALID"
    if stored_state == "AUTHORIZED_CONSUMED":
        return "AUTHORIZED_CONSUMED"
    if stored_state == "AUTHORIZED_UNUSED":
        return "AUTHORIZED_UNUSED"
    return "EXPIRED_OR_INVALID"


def consume_one_shot_authorization(
    repo_root: Path,
    packet: ProviderRunPacket,
    *,
    live_token: str,
) -> AuthorizationState:
    """Mark token consumed at spawn boundary; never rolls back on pytest failure."""

    state = resolve_authorization_state(repo_root, packet, live_token=live_token)
    if state != "AUTHORIZED_UNUSED":
        return state
    ledger_path = authorization_ledger_path(repo_root, packet.change_id)
    _save_authorization_ledger(
        ledger_path,
        one_shot_authorization_id=packet.one_shot_authorization_id,
        authorization_state="AUTHORIZED_CONSUMED",
    )
    return "AUTHORIZED_CONSUMED"


def _blocked_authorization(
    state: AuthorizationState,
    *,
    mismatch_field: str,
) -> GuardVerdict:
    return GuardVerdict(
        status="BLOCKED_AUTHORIZATION",
        mismatch_field=mismatch_field,
        expected="AUTHORIZED_UNUSED",
        computed=state,
        spawn_count=0,
        authorization_state=state,
    )


def _check_authorization(
    repo_root: Path,
    packet: ProviderRunPacket,
    *,
    live_token: str | None,
) -> GuardVerdict | None:
    state = resolve_authorization_state(repo_root, packet, live_token=live_token)
    if state == "AUTHORIZED_UNUSED":
        return None
    if state == "NOT_AUTHORIZED":
        return _blocked_authorization(state, mismatch_field="AUTH_NOT_AUTHORIZED")
    if state == "AUTHORIZED_CONSUMED":
        return _blocked_authorization(state, mismatch_field="AUTH_CONSUMED")
    if state == "EXPIRED_OR_INVALID":
        if live_token and one_shot_authorization_token_sha256(live_token) != (
            packet.one_shot_authorization_id
        ):
            return _blocked_authorization(state, mismatch_field="AUTH_TOKEN_MISMATCH")
        return _blocked_authorization(state, mismatch_field="AUTH_INVALID")
    return _blocked_authorization(state, mismatch_field="AUTH_INVALID")


def verify_provider_run_packet(
    repo_root: Path,
    packet: ProviderRunPacket,
    *,
    compute_head: Callable[[Path], str] | None = None,
    compute_status: Callable[[Path], str] | None = None,
    compute_diff: Callable[[Path], str] | None = None,
    compute_manifest: Callable[[Path], str] | None = None,
    live_token: str | None = None,
) -> GuardVerdict:
    """Сверить packet с текущим worktree; без subprocess pytest."""

    head_fn = compute_head or compute_audited_head
    status_fn = compute_status or compute_audited_status_sha256
    diff_fn = compute_diff or compute_audited_tracked_diff_sha256
    manifest_fn = compute_manifest or compute_audited_untracked_manifest_sha256

    computed_head = head_fn(repo_root)
    if computed_head != packet.audited_head:
        return _blocked("audited_head", packet.audited_head, computed_head)

    computed_status = status_fn(repo_root)
    if computed_status != packet.audited_status_sha256:
        return _blocked(
            "audited_status_sha256",
            packet.audited_status_sha256,
            computed_status,
        )

    computed_diff = diff_fn(repo_root)
    if computed_diff != packet.audited_tracked_diff_sha256:
        return _blocked(
            "audited_tracked_diff_sha256",
            packet.audited_tracked_diff_sha256,
            computed_diff,
        )

    computed_manifest = manifest_fn(repo_root)
    if computed_manifest != packet.audited_untracked_manifest_sha256:
        return _blocked(
            "audited_untracked_manifest_sha256",
            packet.audited_untracked_manifest_sha256,
            computed_manifest,
        )

    computed_block = allowed_run_block_sha256(packet.allowed_run_block_text)
    if computed_block != packet.allowed_run_block_sha256:
        return _blocked(
            "allowed_run_block_sha256",
            packet.allowed_run_block_sha256,
            computed_block,
        )

    block = packet.allowed_run_block_text
    if f"POSTGRES_MASTER_HOST={packet.postgres_host}" not in block:
        return _blocked(
            "postgres_host_in_block",
            packet.postgres_host,
            "missing_or_mismatch",
        )
    if f"POSTGRES_PORT={packet.postgres_port}" not in block:
        return _blocked(
            "postgres_port_in_block",
            str(packet.postgres_port),
            "missing_or_mismatch",
        )
    if f"POSTGRES_DBNAME={packet.postgres_dbname}" not in block:
        return _blocked(
            "postgres_dbname_in_block",
            packet.postgres_dbname,
            "missing_or_mismatch",
        )

    expected_pytest = " ".join(packet.pytest_argv)
    if expected_pytest not in block:
        return _blocked("pytest_argv_in_block", expected_pytest, "missing")

    integration_target = packet.pytest_argv[-1] if packet.pytest_argv else ""
    if integration_target and integration_target not in block:
        return _blocked(
            "pytest_integration_target",
            integration_target,
            "missing_from_block",
        )

    for node_id in packet.provider_test_ids:
        file_part = node_id.split("::", 1)[0]
        parent = str(Path(file_part).parent)
        if (
            file_part not in block
            and parent not in block
            and integration_target not in file_part
        ):
            return _blocked("provider_test_ids", node_id, "not_covered_by_block")

    auth_block = _check_authorization(repo_root, packet, live_token=live_token)
    if auth_block is not None:
        return auth_block

    return GuardVerdict(
        status="PERMIT",
        spawn_count=0,
        authorization_state="AUTHORIZED_UNUSED",
    )


def run_guarded_pytest(
    repo_root: Path,
    packet: ProviderRunPacket,
    *,
    subprocess_runner: Callable[..., Any] | None = None,
    extra_env: Mapping[str, str] | None = None,
    dry_run: bool = False,
    compute_head: Callable[[Path], str] | None = None,
    compute_status: Callable[[Path], str] | None = None,
    compute_diff: Callable[[Path], str] | None = None,
    compute_manifest: Callable[[Path], str] | None = None,
    live_token: str | None = None,
) -> GuardVerdict:
    """Проверить packet; при PERMIT — один subprocess (или dry_run)."""

    verdict = verify_provider_run_packet(
        repo_root,
        packet,
        compute_head=compute_head,
        compute_status=compute_status,
        compute_diff=compute_diff,
        compute_manifest=compute_manifest,
        live_token=live_token,
    )
    if verdict.status != "PERMIT":
        return verdict

    if dry_run:
        return GuardVerdict(
            status="PERMIT",
            spawn_count=0,
            authorization_state="AUTHORIZED_UNUSED",
        )

    if not live_token:
        return _blocked_authorization("NOT_AUTHORIZED", mismatch_field="AUTH_NOT_AUTHORIZED")

    consumed = consume_one_shot_authorization(
        repo_root,
        packet,
        live_token=live_token,
    )
    if consumed != "AUTHORIZED_CONSUMED":
        return _blocked_authorization(consumed, mismatch_field="AUTH_CONSUMED")

    runner = subprocess_runner or subprocess.run
    env = dict(extra_env or {})
    _ = runner(
        list(packet.pytest_argv),
        cwd=repo_root,
        env=env,
        check=False,
    )
    return GuardVerdict(
        status="PERMIT",
        spawn_count=1,
        authorization_state="AUTHORIZED_CONSUMED",
    )


def _load_packet_json(path: Path) -> ProviderRunPacket:
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        return ProviderRunPacket.from_mapping(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED_PACKET_INVALID:{exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: verify | run --packet <json> [--repo ROOT] [--dry-run]."""

    parser = argparse.ArgumentParser(
        description="OPSX provider-run fail-closed fingerprint guard",
    )
    parser.add_argument(
        "mode",
        choices=("verify", "run"),
        help="verify only, or verify then spawn pytest once",
    )
    parser.add_argument(
        "--packet",
        required=True,
        type=Path,
        help="JSON file with ProviderRunPacket fields",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Git worktree root",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run mode: permit without subprocess",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    packet = _load_packet_json(args.packet)
    repo_root = args.repo.resolve()

    live_token = os.environ.get("AUTHORIZE_ONE_LIVE_RUN")

    if args.mode == "verify":
        verdict = verify_provider_run_packet(
            repo_root,
            packet,
            live_token=live_token,
        )
    else:
        verdict = run_guarded_pytest(
            repo_root,
            packet,
            dry_run=args.dry_run,
            live_token=live_token,
        )

    print(json.dumps(verdict.to_dict(), indent=2, sort_keys=True))
    if verdict.status == "BLOCKED_FINGERPRINT_MISMATCH":
        print("BLOCKED_FINGERPRINT_MISMATCH", file=sys.stderr)
        return EXIT_BLOCKED_FINGERPRINT
    if verdict.status == "BLOCKED_AUTHORIZATION":
        print("BLOCKED_AUTHORIZATION", file=sys.stderr)
        return EXIT_BLOCKED_AUTHORIZATION
    if verdict.status == "PERMIT":
        return EXIT_PERMIT
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
