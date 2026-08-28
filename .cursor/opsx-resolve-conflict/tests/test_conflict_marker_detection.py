"""Regression: structural merge-marker detection vs literal substring false positives."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from opsx_conflict.conflict_markers import has_unresolved_merge_markers
from opsx_conflict.models import (
    AuthorityLane,
    ClassifiedConflict,
    ResolutionClass,
    ResolutionKind,
)
from opsx_conflict.verify import (
    detect_logical_conflict_in_cluster,
    validate_synthesis_candidate,
    verify_resolution_unit,
)

RESOLVE_TEXT_MARKER_SNIPPET = '''\
"""Textual resolution strategies."""

import re

_MARKER_START = re.compile(r"^<<<<<<<.*$", re.MULTILINE)
_MARKER_MID = re.compile(r"^=======.*$", re.MULTILINE)
_MARKER_END = re.compile(r"^>>>>>>>.*$", re.MULTILINE)

def helper() -> None:
    # documentation token only: <<<<<<< HEAD
    token = "<<<<<<<"
    pattern = r"^<<<<<<<.*?$"
    _ = pattern
'''

REAL_CONFLICT = """\
line before
<<<<<<< HEAD
ours
=======
theirs
>>>>>>> feature
line after
"""

PARTIAL_CONFLICT = """\
<<<<<<< HEAD
ours only
=======
"""

ORPHAN_SEPARATOR = """\
content
=======
more
"""


@pytest.mark.unit
def test_real_git_conflict_block_is_rejected() -> None:
    assert has_unresolved_merge_markers(REAL_CONFLICT)


@pytest.mark.unit
def test_python_string_literal_with_marker_token_accepted() -> None:
    source = 'value = "prefix <<<<<<< suffix"\n'
    assert not has_unresolved_merge_markers(source)


@pytest.mark.unit
def test_regex_containing_marker_text_accepted() -> None:
    assert not has_unresolved_merge_markers(RESOLVE_TEXT_MARKER_SNIPPET)


@pytest.mark.unit
def test_comment_and_doc_token_do_not_trigger_false_positive() -> None:
    source = "# marker example: <<<<<<< HEAD\n'''not a marker block'''\n"
    assert not has_unresolved_merge_markers(source)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [PARTIAL_CONFLICT, ORPHAN_SEPARATOR, ">>>>>>> feature\n"],
)
def test_partial_or_orphan_structural_markers_rejected(text: str) -> None:
    assert has_unresolved_merge_markers(text)


@pytest.mark.unit
def test_validate_synthesis_candidate_still_rejects_real_markers() -> None:
    ok, refs = validate_synthesis_candidate("module.py", REAL_CONFLICT)
    assert not ok
    assert "validation:conflict_markers_present" in refs


@pytest.mark.unit
def test_validate_synthesis_candidate_accepts_resolve_text_like_source() -> None:
    ok, refs = validate_synthesis_candidate(
        "resolve_text.py",
        RESOLVE_TEXT_MARKER_SNIPPET,
    )
    assert ok
    assert "validation:python_syntax_ok" in refs


@pytest.mark.unit
def test_verify_resolution_unit_accepts_resolve_text_like_source(
    empty_repo: Path,
) -> None:
    repo = empty_repo
    target = repo / ".opsx" / "resolve_text.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(RESOLVE_TEXT_MARKER_SNIPPET, encoding="utf-8")

    classified = ClassifiedConflict(
        conflict_id="x",
        cluster_id=None,
        path=".opsx/resolve_text.py",
        lane=AuthorityLane.PROCESS,
        resolution_class=ResolutionClass.AI_SEMANTIC,
        resolution_kind=ResolutionKind.KEEP_SIDE_A,
        reason="test",
    )
    ok, refs = verify_resolution_unit(repo, classified.path, classified)
    assert ok
    assert "conflict_markers_remain" not in refs


@pytest.mark.unit
def test_detect_logical_conflict_no_false_positive_on_resolve_text_regex(
    empty_repo: Path,
) -> None:
    repo = empty_repo
    cluster_path = ".cursor/opsx-resolve-conflict/runtime/opsx_conflict/resolve_text.py"
    target = repo / cluster_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(RESOLVE_TEXT_MARKER_SNIPPET, encoding="utf-8")

    auto_merged = ["app/consumer.py"]
    consumer = repo / "app" / "consumer.py"
    consumer.parent.mkdir(parents=True, exist_ok=True)
    consumer.write_text("def run() -> None:\n    helper()\n", encoding="utf-8")

    found, reason = detect_logical_conflict_in_cluster(
        repo,
        [cluster_path],
        auto_merged,
    )
    assert not found, reason


@pytest.mark.unit
def test_detect_logical_conflict_still_flags_real_marker_in_cluster_path(
    empty_repo: Path,
) -> None:
    repo = empty_repo
    cluster_path = ".opsx/conflicted.py"
    target = repo / cluster_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(REAL_CONFLICT, encoding="utf-8")

    consumer = repo / "app" / "consumer.py"
    consumer.parent.mkdir(parents=True, exist_ok=True)
    consumer.write_text("def run() -> None:\n    helper()\n", encoding="utf-8")

    found, reason = detect_logical_conflict_in_cluster(
        repo,
        [cluster_path],
        ["app/consumer.py"],
    )
    assert found
    assert "logical:marker_in_related" in reason
