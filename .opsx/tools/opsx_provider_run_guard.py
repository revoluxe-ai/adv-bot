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
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

EXIT_BLOCKED_FINGERPRINT = 3
EXIT_PERMIT = 0
EXIT_USAGE = 2
EXIT_PROVIDER_FAILED = 5
EXIT_PROVIDER_ERROR = 6

GuardStatus = Literal[
    "PERMIT",
    "PROVIDER_PASSED",
    "PROVIDER_FAILED",
    "PROVIDER_ERROR",
    "BLOCKED_FINGERPRINT_MISMATCH",
    "BLOCKED_AUTHORIZATION",
    "BLOCKED_PACKET_INVALID",
]

GuardPermission = Literal["DENIED", "PERMITTED"]

ProviderResult = Literal["NOT_RUN", "PASSED", "FAILED", "ERROR"]

AuthorizationState = Literal[
    "NOT_AUTHORIZED",
    "AUTHORIZED_UNUSED",
    "AUTHORIZED_CONSUMED",
    "EXPIRED_OR_INVALID",
]

OneShotClaimResult = Literal["CLAIMED", "ALREADY_CONSUMED", "NOT_ELIGIBLE"]

EXIT_BLOCKED_AUTHORIZATION = 4

_CANONICAL_PYTEST_ARGV_SHA256_LINE = re.compile(
    r"^#\s*CANONICAL_PYTEST_ARGV_SHA256:\s*([0-9a-f]{64})\s*$"
)


class ProviderSubprocessError(RuntimeError):
    """Subprocess runner returned an unusable result (fail-closed)."""


@dataclass(frozen=True)
class ProviderRunPacket:
    """Ожидаемые поля из INDEPENDENT_REAUDIT + frozen run block."""

    audited_head: str
    audited_status_sha256: str
    audited_tracked_diff_sha256: str
    audited_untracked_manifest_sha256: str
    allowed_run_block_sha256: str
    allowed_run_block_text: str
    canonical_pytest_argv_sha256: str
    pytest_argv: tuple[str, ...]
    pytest_targets: tuple[str, ...]
    provider_test_ids: tuple[str, ...]
    postgres_host: str
    postgres_port: int
    postgres_dbname: str
    redis_host: str
    redis_port: int
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

        targets_raw = _req("pytest_targets")
        pytest_targets = tuple(normalize_repo_posix_path(str(x)) for x in targets_raw)

        port_raw = _req("postgres_port")
        postgres_port = int(port_raw)

        redis_port_raw = _req("redis_port")
        redis_port = int(redis_port_raw)

        canonical_sha = str(_req("canonical_pytest_argv_sha256"))
        computed_argv_sha = canonical_pytest_argv_sha256(pytest_argv)
        if canonical_sha != computed_argv_sha:
            raise ValueError("canonical_pytest_argv_sha256_mismatch")

        return cls(
            audited_head=str(_req("audited_head")),
            audited_status_sha256=str(_req("audited_status_sha256")),
            audited_tracked_diff_sha256=str(_req("audited_tracked_diff_sha256")),
            audited_untracked_manifest_sha256=str(
                _req("audited_untracked_manifest_sha256")
            ),
            allowed_run_block_sha256=str(_req("allowed_run_block_sha256")),
            allowed_run_block_text=str(_req("allowed_run_block_text")),
            canonical_pytest_argv_sha256=canonical_sha,
            pytest_argv=pytest_argv,
            pytest_targets=pytest_targets,
            provider_test_ids=provider_test_ids,
            postgres_host=str(_req("postgres_host")),
            postgres_port=postgres_port,
            postgres_dbname=str(_req("postgres_dbname")),
            redis_host=str(_req("redis_host")),
            redis_port=redis_port,
            change_id=str(_req("change_id")),
            one_shot_authorization_id=str(_req("one_shot_authorization_id")),
        )


@dataclass(frozen=True)
class GuardVerdict:
    """Результат проверки guard и (опционально) provider subprocess."""

    status: GuardStatus
    mismatch_field: str | None = None
    expected: str | None = None
    computed: str | None = None
    spawn_count: int = 0
    authorization_state: AuthorizationState | None = None
    guard_permission: GuardPermission = "DENIED"
    provider_spawned: bool = False
    provider_return_code: int | None = None
    provider_result: ProviderResult = "NOT_RUN"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_bytes(payload: bytes) -> str:
    """SHA-256 lowercase hex от точных байт stdout/блока."""

    return hashlib.sha256(payload).hexdigest()


def normalize_repo_posix_path(raw: str) -> str:
    """Repo-relative path in POSIX form (host OS must not affect verification)."""

    replaced = raw.replace("\\", "/")
    if replaced.endswith("/") and len(replaced) > 1:
        base = PurePosixPath(replaced.rstrip("/")).as_posix()
        return f"{base}/"
    return PurePosixPath(replaced).as_posix()


def extract_pytest_targets_from_argv(argv: Sequence[str]) -> tuple[str, ...]:
    """Collect repo-relative test paths from argv; stop before pytest options."""

    tokens = list(argv)
    if "pytest" not in tokens:
        return ()
    idx = tokens.index("pytest") + 1
    targets: list[str] = []
    option_with_value = frozenset(
        {"-m", "-k", "--markers", "--keyword", "--tb", "--maxfail"}
    )
    i = idx
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("-"):
            if tok in option_with_value and i + 1 < len(tokens):
                i += 2
                continue
            if "=" in tok:
                i += 1
                continue
            break
        targets.append(normalize_repo_posix_path(tok))
        i += 1
    return tuple(targets)


def provider_test_id_within_targets(
    node_id: str,
    pytest_targets: Sequence[str],
) -> bool:
    """True when node file path is under a sealed POSIX pytest target."""

    file_part = normalize_repo_posix_path(node_id.split("::", 1)[0])
    file_path = PurePosixPath(file_part)
    for target in pytest_targets:
        target_norm = normalize_repo_posix_path(target)
        target_path = PurePosixPath(target_norm.rstrip("/"))
        if target_norm.endswith("/") or target_path.suffix == "":
            try:
                file_path.relative_to(target_path)
                return True
            except ValueError:
                continue
        if file_path == target_path:
            return True
    return False


def canonical_pytest_argv_sha256(argv: Sequence[str]) -> str:
    """Stable hash of the exact provider subprocess argv tuple."""

    payload = json.dumps(list(argv), separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(payload.encode("utf-8"))


def provider_run_spec_sha256(
    *,
    allowed_run_block_sha256: str,
    canonical_pytest_argv_sha256: str,
) -> str:
    """Hash binding frozen orchestration block to canonical executable argv."""

    payload = json.dumps(
        {
            "allowed_run_block_sha256": allowed_run_block_sha256,
            "canonical_pytest_argv_sha256": canonical_pytest_argv_sha256,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256_bytes(payload.encode("utf-8"))


def block_has_unguarded_pytest_invocation(block_text: str) -> bool:
    """True when a non-comment line would spawn pytest outside guard run."""

    pytest_token = re.compile(r"(^|[^\w])(pytest|py\.test)([^\w]|$)", re.IGNORECASE)
    for line in block_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "opsx_provider_run_guard.py" in stripped:
            continue
        lowered = stripped.lower()
        if pytest_token.search(stripped):
            return True
        if "python" in lowered and "-m pytest" in lowered:
            return True
        if lowered.startswith("poetry run pytest"):
            return True
    return False


def canonical_pytest_argv_sha256_in_block(
    block_text: str,
) -> str | None:
    """Extract sealed canonical argv hash comment from frozen block, if present."""

    for line in block_text.splitlines():
        match = _CANONICAL_PYTEST_ARGV_SHA256_LINE.match(line.strip())
        if match:
            return match.group(1)
    return None


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
        guard_permission="DENIED",
    )


def one_shot_authorization_token_sha256(token: str) -> str:
    """SHA-256 fingerprint of ``AUTHORIZE_ONE_LIVE_RUN`` secret (UTF-8)."""

    return sha256_bytes(token.encode("utf-8"))


def authorization_ledger_path(
    repo_root: Path,
    change_id: str,
    one_shot_authorization_id: str,
) -> Path:
    """Per-token durable consumption claim file (cross-process one-shot)."""

    return (
        repo_root
        / ".opsx"
        / "runs"
        / "scenario-coverage"
        / change_id
        / "authorizations"
        / f"{one_shot_authorization_id}.json"
    )


def _load_authorization_ledger(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _authorization_ledger_payload(
    *,
    one_shot_authorization_id: str,
) -> bytes:
    payload = {
        "one_shot_authorization_id": one_shot_authorization_id,
        "authorization_state": "AUTHORIZED_CONSUMED",
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


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
    ledger_path = authorization_ledger_path(
        repo_root,
        packet.change_id,
        packet.one_shot_authorization_id,
    )
    if not ledger_path.is_file():
        return "AUTHORIZED_UNUSED"
    ledger = _load_authorization_ledger(ledger_path)
    if ledger is None:
        return "AUTHORIZED_UNUSED"
    stored_id = str(ledger.get("one_shot_authorization_id", ""))
    stored_state = str(ledger.get("authorization_state", ""))
    if stored_id != packet.one_shot_authorization_id:
        return "EXPIRED_OR_INVALID"
    if stored_state == "AUTHORIZED_CONSUMED":
        return "AUTHORIZED_CONSUMED"
    return "EXPIRED_OR_INVALID"


def try_claim_one_shot_authorization(
    repo_root: Path,
    packet: ProviderRunPacket,
    *,
    live_token: str,
) -> OneShotClaimResult:
    """Atomically claim one-shot authorization (O_CREAT|O_EXCL); never rolls back."""

    state = resolve_authorization_state(repo_root, packet, live_token=live_token)
    if state != "AUTHORIZED_UNUSED":
        if state == "AUTHORIZED_CONSUMED":
            return "ALREADY_CONSUMED"
        return "NOT_ELIGIBLE"
    ledger_path = authorization_ledger_path(
        repo_root,
        packet.change_id,
        packet.one_shot_authorization_id,
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _authorization_ledger_payload(
        one_shot_authorization_id=packet.one_shot_authorization_id,
    )
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(ledger_path), flags)
        try:
            _ = os.write(fd, payload)
        finally:
            os.close(fd)
        return "CLAIMED"
    except FileExistsError:
        return "ALREADY_CONSUMED"


def consume_one_shot_authorization(
    repo_root: Path,
    packet: ProviderRunPacket,
    *,
    live_token: str,
) -> AuthorizationState:
    """Legacy wrapper: successful claim → AUTHORIZED_CONSUMED."""

    claim = try_claim_one_shot_authorization(
        repo_root,
        packet,
        live_token=live_token,
    )
    if claim == "CLAIMED":
        return "AUTHORIZED_CONSUMED"
    if claim == "ALREADY_CONSUMED":
        return "AUTHORIZED_CONSUMED"
    return resolve_authorization_state(repo_root, packet, live_token=live_token)


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
        guard_permission="DENIED",
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


def build_provider_subprocess_env(
    packet: ProviderRunPacket,
    *,
    parent_env: Mapping[str, str] | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Child pytest env: inherit parent (PATH, Poetry), bind audited test coordinates."""

    env = dict(parent_env if parent_env is not None else os.environ)
    env.update(
        {
            "POSTGRES_MASTER_HOST": packet.postgres_host,
            "POSTGRES_REPLICA_HOST": packet.postgres_host,
            "POSTGRES_PORT": str(packet.postgres_port),
            "POSTGRES_DBNAME": packet.postgres_dbname,
            "ALLOW_DESTRUCTIVE_TEST_DB": "1",
            "ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE": "1",
            "REDIS_HOST": packet.redis_host,
            "REDIS_PORT": str(packet.redis_port),
        }
    )
    if extra_env:
        env.update(extra_env)
    return env


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
    if f"REDIS_HOST={packet.redis_host}" not in block:
        return _blocked(
            "redis_host_in_block",
            packet.redis_host,
            "missing_or_mismatch",
        )
    if f"REDIS_PORT={packet.redis_port}" not in block:
        return _blocked(
            "redis_port_in_block",
            str(packet.redis_port),
            "missing_or_mismatch",
        )

    extracted_targets = extract_pytest_targets_from_argv(packet.pytest_argv)
    if tuple(packet.pytest_targets) != extracted_targets:
        return _blocked(
            "pytest_targets",
            ",".join(packet.pytest_targets),
            ",".join(extracted_targets),
        )

    computed_argv_sha = canonical_pytest_argv_sha256(packet.pytest_argv)
    if computed_argv_sha != packet.canonical_pytest_argv_sha256:
        return _blocked(
            "canonical_pytest_argv_sha256",
            packet.canonical_pytest_argv_sha256,
            computed_argv_sha,
        )

    block_argv_sha = canonical_pytest_argv_sha256_in_block(block)
    if block_argv_sha is None:
        return _blocked(
            "canonical_pytest_argv_sha256_in_block",
            packet.canonical_pytest_argv_sha256,
            "missing",
        )
    if block_argv_sha != packet.canonical_pytest_argv_sha256:
        return _blocked(
            "canonical_pytest_argv_sha256_in_block",
            packet.canonical_pytest_argv_sha256,
            block_argv_sha,
        )

    guard_run_fragment = (
        "opsx_provider_run_guard.py run --packet"
    )
    if guard_run_fragment not in block:
        return _blocked("guard_run_in_block", guard_run_fragment, "missing")

    if block_has_unguarded_pytest_invocation(block):
        return _blocked(
            "unguarded_pytest_in_block",
            "forbidden",
            "direct_pytest_invocation",
        )

    for node_id in packet.provider_test_ids:
        if not provider_test_id_within_targets(node_id, packet.pytest_targets):
            return _blocked("provider_test_ids", node_id, "not_covered_by_targets")

    auth_block = _check_authorization(repo_root, packet, live_token=live_token)
    if auth_block is not None:
        return auth_block

    return GuardVerdict(
        status="PERMIT",
        spawn_count=0,
        authorization_state="AUTHORIZED_UNUSED",
        guard_permission="PERMITTED",
        provider_result="NOT_RUN",
    )


def resolve_subprocess_returncode(result: Any) -> int:
    """Extract return code from subprocess runner result; fail closed if unknown."""

    if result is None:
        raise ProviderSubprocessError("subprocess_runner_returned_none")
    returncode = getattr(result, "returncode", None)
    if returncode is None:
        raise ProviderSubprocessError("subprocess_result_missing_returncode")
    return int(returncode)


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
            guard_permission="PERMITTED",
            provider_result="NOT_RUN",
        )

    if not live_token:
        return _blocked_authorization("NOT_AUTHORIZED", mismatch_field="AUTH_NOT_AUTHORIZED")

    claim = try_claim_one_shot_authorization(
        repo_root,
        packet,
        live_token=live_token,
    )
    if claim != "CLAIMED":
        state = resolve_authorization_state(
            repo_root,
            packet,
            live_token=live_token,
        )
        if claim == "NOT_ELIGIBLE" and state == "NOT_AUTHORIZED":
            return _blocked_authorization(state, mismatch_field="AUTH_NOT_AUTHORIZED")
        if claim == "NOT_ELIGIBLE" and state == "EXPIRED_OR_INVALID":
            return _blocked_authorization(state, mismatch_field="AUTH_INVALID")
        return _blocked_authorization(
            "AUTHORIZED_CONSUMED",
            mismatch_field="AUTH_CONSUMED",
        )

    runner = subprocess_runner or subprocess.run
    env = build_provider_subprocess_env(packet, extra_env=extra_env)
    try:
        completed = runner(
            list(packet.pytest_argv),
            cwd=repo_root,
            env=env,
            check=False,
        )
        returncode = resolve_subprocess_returncode(completed)
    except Exception:
        return GuardVerdict(
            status="PROVIDER_ERROR",
            spawn_count=1,
            authorization_state="AUTHORIZED_CONSUMED",
            guard_permission="PERMITTED",
            provider_spawned=True,
            provider_return_code=None,
            provider_result="ERROR",
        )

    if returncode == 0:
        return GuardVerdict(
            status="PROVIDER_PASSED",
            spawn_count=1,
            authorization_state="AUTHORIZED_CONSUMED",
            guard_permission="PERMITTED",
            provider_spawned=True,
            provider_return_code=returncode,
            provider_result="PASSED",
        )
    return GuardVerdict(
        status="PROVIDER_FAILED",
        spawn_count=1,
        authorization_state="AUTHORIZED_CONSUMED",
        guard_permission="PERMITTED",
        provider_spawned=True,
        provider_return_code=returncode,
        provider_result="FAILED",
    )


def _load_packet_json(path: Path) -> ProviderRunPacket:
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        return ProviderRunPacket.from_mapping(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED_PACKET_INVALID:{exc}") from exc


def cli_exit_code_for_verdict(verdict: GuardVerdict) -> int:
    """Map guard verdict to process exit code (guard vs provider execution)."""

    if verdict.status == "BLOCKED_FINGERPRINT_MISMATCH":
        return EXIT_BLOCKED_FINGERPRINT
    if verdict.status == "BLOCKED_AUTHORIZATION":
        return EXIT_BLOCKED_AUTHORIZATION
    if verdict.status in ("PERMIT", "PROVIDER_PASSED"):
        return EXIT_PERMIT
    if verdict.status == "PROVIDER_FAILED":
        return EXIT_PROVIDER_FAILED
    if verdict.status == "PROVIDER_ERROR":
        return EXIT_PROVIDER_ERROR
    return EXIT_USAGE


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
    elif verdict.status == "BLOCKED_AUTHORIZATION":
        print("BLOCKED_AUTHORIZATION", file=sys.stderr)
    elif verdict.status == "PROVIDER_FAILED":
        print("PROVIDER_FAILED", file=sys.stderr)
    elif verdict.status == "PROVIDER_ERROR":
        print("PROVIDER_ERROR", file=sys.stderr)
    return cli_exit_code_for_verdict(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
