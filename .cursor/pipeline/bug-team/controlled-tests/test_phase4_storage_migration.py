# -*- coding: utf-8 -*-
"""Phase 4 storage migration process tests (cases A–P).

Automatable checks for `.tmp` → `.opsx/runs` durable store migration without
invoking Cursor agents. Run:

    poetry run pytest -m unit .cursor/pipeline/bug-team/controlled-tests/test_phase4_storage_migration.py -v

or:

    python .cursor/pipeline/bug-team/controlled-tests/test_phase4_storage_migration.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]

CASE_IDS = [
    "BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z",
    "BUGCASE-CAH-CONFIRM-20260821-001",
    "BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z",
    "BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z",
]

BOOTSTRAP_UTC = [
    "20260812T212312Z",
    "20260812T212441Z",
    "20260812T212501Z",
    "20260812T212652Z",
    "20260812T213453Z",
]

ACTIVE_SCAN_ROOTS = [
    REPO / ".cursor" / "commands",
    REPO / ".cursor" / "pipeline",
    REPO / ".opsx" / "shared",
    REPO / ".opsx" / "import",
    REPO / ".opsx" / "sources.yaml",
    REPO / ".cursor" / "opsx-resolve-conflict" / "process_surfaces.json",
    REPO / ".cursor" / "opsx-export" / "export_bundle.py",
]

ACTIVE_COMMAND_SAMPLES = [
    REPO / ".cursor/commands/opsx-fix-bug.md",
    REPO / ".cursor/commands/opsx-bug-team.md",
    REPO / ".cursor/commands/opsx-materialize-bug-queue.md",
    REPO / ".cursor/commands/opsx-claim-next-bug.md",
]

LIVE_SOT_SUBDIRS = ("findings", "results")

HISTORICAL_EXCLUDE = {
    REPO / ".opsx/registry/provenance.ndjson",
    REPO / ".opsx/project/manual_review.md",
}

HISTORICAL_GLOB = re.compile(
    r"(CORRECTIVE_V\d|controlled-tests/_phase4|controlled-tests/test_phase4)"
)

DURABLE_TMP_RE = re.compile(
    r"\.tmp/opsx-(bug-cases|bootstrap|inbound|scenario-coverage|distribute)"
)

EPHEMERAL_OK_PATTERNS = [
    re.compile(r"\.tmp/opsx-chat-audit"),
    re.compile(r"\.tmp/opsx-devops"),
    re.compile(r"\.tmp/opsx-bug-team-harness"),
    re.compile(r"opsx-meta-bootstrap\.md.*\.tmp/opsx-bootstrap"),
    re.compile(r"bootstrap-profile\.md.*\.tmp/opsx-bootstrap/<UTC>"),
    re.compile(r"ephemeral.*\.tmp/opsx-bootstrap"),
    re.compile(r"Staging only:.*\.tmp/opsx-bootstrap"),
    re.compile(r"DIFF only"),
    re.compile(r"does NOT create real \.tmp/opsx-bug-cases"),
    re.compile(r"OLD_BUG|OLD_BOOT|_phase4_storage_migration"),
]


def _run_git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout


def _iter_active_files() -> list[Path]:
    files: list[Path] = []
    for root in ACTIVE_SCAN_ROOTS:
        if root.is_file():
            files.append(root)
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix == ".pyc" or "__pycache__" in path.parts:
                continue
            if path in HISTORICAL_EXCLUDE:
                continue
            rel = str(path.relative_to(REPO)).replace("\\", "/")
            if HISTORICAL_GLOB.search(rel):
                continue
            if "/harness/" in rel:
                continue
            files.append(path)
    return files


def _ephemeral_tmp_ok(path: Path, text: str, match: re.Match[str]) -> bool:
    rel = str(path.relative_to(REPO)).replace("\\", "/")
    if rel.endswith(".opsx/shared/bootstrap-profile.md"):
        return ".tmp/opsx-bootstrap/<UTC>/" in text
    if rel.endswith(".cursor/commands/opsx-meta-bootstrap.md"):
        return True
    snippet = text[max(0, match.start() - 80) : match.end() + 80]
    return any(p.search(snippet) or p.search(text) for p in EPHEMERAL_OK_PATTERNS)


@pytest.mark.unit
def test_a_gitignore_tmp_probe() -> None:
    """A: .tmp/probe is gitignored."""
    out = _run_git("check-ignore", "-v", ".tmp/probe")
    assert ".tmp/probe" in out or "probe" in out


@pytest.mark.unit
def test_b_active_surfaces_use_opsx_runs() -> None:
    """B: active commands/contracts reference .opsx/runs for durable bug-cases."""
    for path in ACTIVE_COMMAND_SAMPLES:
        assert path.is_file(), f"missing active command sample: {path}"
        text = path.read_text(encoding="utf-8")
        assert ".opsx/runs/bug-cases" in text, f"{path.name} missing .opsx/runs/bug-cases"
        assert ".tmp/opsx-bug-cases" not in text, f"{path.name} still has .tmp/opsx-bug-cases"

    surfaces = (
        REPO / ".cursor/opsx-resolve-conflict/process_surfaces.json"
    ).read_text(encoding="utf-8")
    assert ".opsx/runs/bug-cases" in surfaces
    assert ".tmp/opsx-bug-cases" not in surfaces

    sources = (REPO / ".opsx/sources.yaml").read_text(encoding="utf-8")
    assert ".opsx/runs/**" in sources
    assert ".tmp/opsx-bug-cases" not in sources


@pytest.mark.unit
def test_c_index_exists() -> None:
    """C: INDEX at canonical bug-cases path."""
    index = REPO / ".opsx/runs/bug-cases/INDEX.md"
    assert index.is_file()


@pytest.mark.unit
def test_d_h_recovery_paths_no_tmp() -> None:
    """D/H: live recovery rows in INDEX omit .tmp/opsx-bug-cases."""
    text = (REPO / ".opsx/runs/bug-cases/INDEX.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if "HUMAN_SUMMARY:" in line or "OWNER_CLOSURE:" in line:
            assert ".tmp/opsx-bug-cases" not in line
            assert ".opsx/runs/bug-cases" in line


@pytest.mark.unit
def test_e_four_case_dirs() -> None:
    """E: four durable CASE directories present."""
    bug_root = REPO / ".opsx/runs/bug-cases"
    for case_id in CASE_IDS:
        assert (bug_root / case_id).is_dir()


@pytest.mark.unit
def test_f_no_temporal_runs_invented() -> None:
    """F: no invented temporal/runs namespace."""
    assert not (REPO / "temporal/runs").exists()
    assert not (REPO / ".opsx/temporal").exists()


@pytest.mark.unit
def test_g_no_post_deploy_acceptance_invented() -> None:
    """G: no post-deploy-acceptance artifact tree invented."""
    assert not (REPO / "post-deploy-acceptance").exists()


@pytest.mark.unit
def test_ij_no_active_durable_tmp_refs() -> None:
    """I/J: zero ACTIVE durable .tmp/opsx-* refs in scoped surfaces."""
    hits: list[str] = []
    for path in _iter_active_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in DURABLE_TMP_RE.finditer(text):
            if _ephemeral_tmp_ok(path, text, m):
                continue
            hits.append(f"{path.relative_to(REPO)}:{m.group(0)}")
    assert not hits, "ACTIVE durable .tmp refs remain:\n" + "\n".join(hits[:20])


@pytest.mark.unit
def test_k_no_dual_write_instructions() -> None:
    """K: no dual-write of same durable object to .tmp and .opsx/runs."""
    dual = re.compile(
        r"(?<!NO )(?<!no )dual[- ]write.*\.tmp.*\.opsx/runs|"
        r"mirror.*\.tmp/.*\.opsx/runs|"
        r"write\s+of\s+same\s+durable\s+object\s+to\s+both",
        re.I,
    )
    for path in _iter_active_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        assert not dual.search(text), f"dual-write hint in {path}"


@pytest.mark.unit
def test_l_live_pointers_and_case_ids() -> None:
    """L: CASE/LEDGER/INDEX live pointers use .opsx/runs; CASE_IDs preserved."""
    bug_root = REPO / ".opsx/runs/bug-cases"
    for case_id in CASE_IDS:
        case_dir = bug_root / case_id
        for name in ("INDEX.md", "CASE.md", "LEDGER.md"):
            path = case_dir / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            assert case_id in text, f"{case_id}/{name} missing CASE_ID"
            assert ".tmp/opsx-bug-cases" not in text, f"{case_id}/{name} has stale .tmp"
            if name == "CASE.md" and "DUPLICATE_SEARCH_ROOT:" in text:
                assert "DUPLICATE_SEARCH_ROOT: .opsx/runs/bug-cases" in text
            if name == "INDEX.md" and "PARENT_INDEX:" in text:
                assert "PARENT_INDEX: .opsx/runs/bug-cases/INDEX.md" in text
            if "ROUTE_TRACE_PATH:" in text:
                assert f".opsx/runs/bug-cases/{case_id}/" in text


@pytest.mark.unit
def test_m_historical_files_keep_tmp_strings() -> None:
    """M: provenance/manual_review retain historical .tmp paths."""
    prov = (REPO / ".opsx/registry/provenance.ndjson").read_text(encoding="utf-8")
    manual = (REPO / ".opsx/project/manual_review.md").read_text(encoding="utf-8")
    assert ".tmp/opsx-bootstrap" in prov
    assert ".tmp/opsx-bootstrap" in manual


@pytest.mark.unit
def test_n_git_ls_files_sees_opsx_runs() -> None:
    """N: git index knows durable .opsx/runs paths (after git add)."""
    tracked = _run_git("ls-files", ".opsx/runs").strip().splitlines()
    tracked_set = {line.replace("\\", "/") for line in tracked if line}
    assert ".opsx/runs/README.md" in tracked_set
    assert ".opsx/runs/bug-cases/INDEX.md" in tracked_set
    for utc in BOOTSTRAP_UTC:
        assert f".opsx/runs/bootstrap/{utc}/MERGE_RECEIPT.md" in tracked_set


@pytest.mark.unit
def test_o_product_trees_untouched() -> None:
    """O: no diff in product trees from this migration."""
    for tree in ("app", "tests", "k8s", "alembic_"):
        diff = _run_git("diff", "--", tree)
        assert diff.strip() == "", f"unexpected diff in {tree}"


@pytest.mark.unit
def test_p_sources_yaml_allowlist() -> None:
    """P: sources.yaml allowlists .opsx/runs/** and export tooling."""
    text = (REPO / ".opsx/sources.yaml").read_text(encoding="utf-8")
    assert ".opsx/runs/**" in text
    assert ".cursor/opsx-export/**" in text


@pytest.mark.unit
def test_q_candidate_report_historical_tmp() -> None:
    """Q: CANDIDATE_REPORT retains historical .tmp/opsx-bug-cases PACKET_FORMAT."""
    text = (REPO / ".cursor/pipeline/bug-team/CANDIDATE_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert ".tmp/opsx-bug-cases" in text


@pytest.mark.unit
def test_r_export_bundle_default_opsx_export() -> None:
    """R: export_bundle default out_dir is repo-root opsx-export/."""
    text = (REPO / ".cursor/opsx-export/export_bundle.py").read_text(encoding="utf-8")
    assert 'repo_root / "opsx-export"' in text
    assert 'repo_root / ".tmp" / "opsx-export"' not in text
    assert "<repo>/opsx-export" in text
    assert "<repo>/.tmp/opsx-export" not in text


@pytest.mark.unit
def test_s_hop_scratch_not_tracked() -> None:
    """S: hop-scratch _* under team/packets are gitignored, not indexed."""
    tracked = {
        line.replace("\\", "/")
        for line in _run_git("ls-files", ".opsx/runs").splitlines()
        if line
    }
    hop_scratch = list((REPO / ".opsx/runs").rglob("team/packets/_*"))
    assert hop_scratch, "expected hop-scratch samples under team/packets/_*"
    for path in hop_scratch:
        rel = path.relative_to(REPO).as_posix()
        assert rel not in tracked, f"hop-scratch tracked: {rel}"
        ignore_out = _run_git("check-ignore", "-v", rel)
        assert rel in ignore_out or path.name in ignore_out


@pytest.mark.unit
def test_t_live_sot_no_durable_tmp() -> None:
    """T: live SoT (INDEX/CASE/LEDGER/findings/results) omit durable .tmp paths."""
    bug_root = REPO / ".opsx/runs/bug-cases"
    paths: list[Path] = [bug_root / "INDEX.md"]
    for case_id in CASE_IDS:
        case_dir = bug_root / case_id
        for name in ("INDEX.md", "CASE.md", "LEDGER.md"):
            p = case_dir / name
            if p.is_file():
                paths.append(p)
        for sub in LIVE_SOT_SUBDIRS:
            subdir = case_dir / sub
            if subdir.is_dir():
                paths.extend(sorted(subdir.rglob("*")))
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        assert ".tmp/opsx-bug-cases" not in text, (
            f"live SoT still references .tmp: {path.relative_to(REPO)}"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
