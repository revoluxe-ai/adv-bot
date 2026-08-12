"""Bounded read-only repository context for PREVIEW_ONLY evidence (R35–R37).

Deterministic evidence layer: enumerates/reads/searches under the repository
root without shell/rg subprocesses. Never writes. Symlink/path escapes STOP.

R36: pathname alone never proves normative authority. Recommendation consumers
must require ``authority_verified=true`` on strong classes.

R37: CONTRACT explicit non-active lifecycle always vetoes before normative
marker acceptance.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .errors import PolicyViolation, StopRequired
from .pathsafety import normalize_repo_rel

CONTEXT_PACKET_SCHEMA = "opsx-resolve-conflict/preview-context/v2"

# Search / read budgets (package-owned defaults).
MAX_SEARCH_INTENTS = 3
MAX_CANDIDATE_FILES_PER_INTENT = 50
MAX_EVIDENCE_ITEMS = 20
MAX_EXCERPT_BYTES_TOTAL = 20 * 1024
MAX_FILE_BYTES = 256 * 1024
MAX_ENUMERATE_FILES = 2000
MAX_BYTES_READ = 512 * 1024

AUTHORITY_CLASSES = frozenset(
    {
        "ACCEPTED_DECISION",
        "CURRENT_SPEC",
        "CONTRACT",
        "API_INVARIANT",
        "TEST_EVIDENCE",
        "SIBLING_IMPLEMENTATION",
        "SOURCE_CODE",
        "BUG_DEBT_EVIDENCE",
        "CHANGE_CONTEXT",
        "UNKNOWN",
    }
)

STRONG_AUTHORITY_CLASSES = frozenset(
    {
        "ACCEPTED_DECISION",
        "CURRENT_SPEC",
        "CONTRACT",
        "API_INVARIANT",
    }
)

# Canonical normative locations (path is necessary but never sufficient).
_CANONICAL_DECISIONS = ("openspec/decisions/",)
_CANONICAL_CURRENT_SPECS = ("openspec/specs/",)
_CANONICAL_CONTRACTS = ("openspec/contracts/",)
_DECISION_INDEX_REL = "openspec/decisions/index.md"

_STATUS_RE = re.compile(
    r"(?im)^\s*(?:status|lifecycle_status)\s*[:=]\s*([A-Za-z_][A-Za-z0-9_-]*)\s*$"
)
_NON_ACCEPTED = frozenset(
    {
        "draft",
        "proposed",
        "rejected",
        "superseded",
        "unknown",
        "pending",
        "wip",
        "deprecated",
    }
)

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        ".tox",
    }
)

_TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".md",
        ".txt",
        ".rst",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".sql",
        ".prompt.md",
    }
)

_DEF_RE = re.compile(
    r"^\s*(?:async\s+)?def\s+(\w+)\s*\(|^\s*class\s+(\w+)\s*[\(:]",
    flags=re.M,
)


@dataclass
class SearchBudget:
    """Mutable counters for bounded context collection."""

    intents_used: int = 0
    candidates_scanned: int = 0
    evidence_items: int = 0
    excerpt_bytes: int = 0
    files_enumerated: int = 0
    bytes_read: int = 0
    exhausted: list[str] = field(default_factory=list)

    def note_exhaustion(self, reason: str) -> None:
        """Record a budget exhaustion reason (idempotent append)."""
        if reason not in self.exhausted:
            self.exhausted.append(reason)


@dataclass
class EvidenceItem:
    """One bounded repository evidence item with authority class + verification."""

    evidence_id: str
    authority_class: str
    authority_verified: bool
    authority_basis: str
    lifecycle_status: str | None
    path: str
    line_start: int
    line_end: int
    excerpt: str
    match_reason: str
    test_kind: str | None = None  # characterization | contract | integration | UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        """Serialize evidence item for the context packet."""
        out: dict[str, Any] = {
            "evidence_id": self.evidence_id,
            "authority_class": self.authority_class,
            "authority_verified": self.authority_verified,
            "authority_basis": self.authority_basis,
            "lifecycle_status": self.lifecycle_status,
            "path": self.path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "excerpt": self.excerpt,
            "match_reason": self.match_reason,
        }
        if self.test_kind is not None:
            out["test_kind"] = self.test_kind
        return out


class BoundedContextReader:
    """Package-owned read-only repository reader (no subprocess)."""

    def __init__(self, repo_root: Path) -> None:
        """Bind to a resolved repository root."""
        self.repo_root = Path(repo_root).resolve()
        self.budget = SearchBudget()
        self._evidence: list[EvidenceItem] = []
        self._id_seq = 0

    def _next_id(self, prefix: str) -> str:
        self._id_seq += 1
        return f"{prefix}-{self._id_seq:03d}"

    def _rel_of(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo_root).as_posix()
        except ValueError as exc:
            raise StopRequired(
                "PREVIEW_CONTEXT_PATH_ESCAPE",
                {"path": str(path), "repo": str(self.repo_root)},
            ) from exc

    def _assert_safe_file(self, path: Path) -> str:
        """Reject symlinks and path escapes; return repo-relative path."""
        if path.is_symlink():
            raise StopRequired(
                "PREVIEW_CONTEXT_SYMLINK_BLOCKED",
                {"path": str(path)},
            )
        # Walk parents for symlink components.
        cur = path
        while True:
            if cur == self.repo_root:
                break
            if cur.is_symlink():
                raise StopRequired(
                    "PREVIEW_CONTEXT_SYMLINK_BLOCKED",
                    {"path": str(cur)},
                )
            if cur.parent == cur:
                break
            cur = cur.parent
        rel = self._rel_of(path)
        try:
            normalize_repo_rel(rel)
        except PolicyViolation as exc:
            raise StopRequired(
                "PREVIEW_CONTEXT_PATH_ESCAPE",
                {"path": rel, "detail": str(exc)},
            ) from exc
        resolved = path.resolve()
        try:
            resolved.relative_to(self.repo_root)
        except ValueError as exc:
            raise StopRequired(
                "PREVIEW_CONTEXT_PATH_ESCAPE",
                {"path": rel, "resolved": str(resolved)},
            ) from exc
        return rel

    def iter_regular_files(self) -> Iterator[Path]:
        """Yield regular non-symlink files under the repo (budgeted)."""
        stack = [self.repo_root]
        while stack:
            directory = stack.pop()
            try:
                entries = list(directory.iterdir())
            except OSError:
                continue
            for entry in entries:
                if self.budget.files_enumerated >= MAX_ENUMERATE_FILES:
                    self.budget.note_exhaustion("max_enumerate_files")
                    return
                name = entry.name
                if name in _SKIP_DIR_NAMES:
                    continue
                if entry.is_symlink():
                    # Symlink dirs/files are skipped during enumeration; explicit
                    # read of a symlink path STOPs.
                    continue
                if entry.is_dir():
                    stack.append(entry)
                    continue
                if entry.is_file():
                    self.budget.files_enumerated += 1
                    yield entry

    def read_text_file(self, path: Path) -> str | None:
        """Read UTF-8 text file or return None if binary/oversized/skip policy."""
        self._assert_safe_file(path)
        if self.budget.bytes_read >= MAX_BYTES_READ:
            self.budget.note_exhaustion("max_bytes_read")
            return None
        try:
            size = path.stat().st_size
        except OSError:
            return None
        if size > MAX_FILE_BYTES:
            return None
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        if b"\x00" in raw[:8192]:
            return None
        self.budget.bytes_read += len(raw)
        if self.budget.bytes_read > MAX_BYTES_READ:
            self.budget.note_exhaustion("max_bytes_read")
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def _can_add_evidence(self, excerpt: str) -> bool:
        if self.budget.evidence_items >= MAX_EVIDENCE_ITEMS:
            self.budget.note_exhaustion("max_evidence_items")
            return False
        enc = excerpt.encode("utf-8")
        if self.budget.excerpt_bytes + len(enc) > MAX_EXCERPT_BYTES_TOTAL:
            self.budget.note_exhaustion("max_excerpt_bytes")
            return False
        return True

    def _authority_excerpt(
        self, *, path: str, full_text: str | None, fallback: str
    ) -> tuple[str, int, int]:
        """Build an excerpt that retains status + contract polarity cues."""
        if not full_text:
            return fallback[:800], 1, max(1, fallback.count("\n") + 1)
        lines = full_text.splitlines()
        keep: list[int] = []
        for i, line in enumerate(lines):
            low = line.lower()
            if _STATUS_RE.match(line) or any(
                tok in low
                for tok in (
                    "existing-users-only",
                    "existing users only",
                    "existing_users_only",
                    "full /start alias",
                    "full start alias",
                    "create path",
                    "read_only",
                    "contract_kind",
                    "normative",
                )
            ):
                keep.extend(range(max(0, i - 1), min(len(lines), i + 2)))
        if not keep:
            return fallback[:800], 1, min(12, len(lines))
        start = min(keep) + 1
        end = max(keep) + 1
        excerpt = "\n".join(lines[start - 1 : end])[:800]
        return excerpt, start, end

    def add_evidence(
        self,
        *,
        authority_class: str | None = None,
        path: str,
        line_start: int,
        line_end: int,
        excerpt: str,
        match_reason: str,
        full_text: str | None = None,
        test_kind: str | None = None,
        id_prefix: str = "E",
        decision_index_text: str | None = None,
    ) -> EvidenceItem | None:
        """Append an evidence item if budgets allow; verify authority from content."""
        text_for_verify = full_text if full_text is not None else excerpt
        verified = verify_authority(
            path,
            text_for_verify,
            provisional_class=authority_class,
            decision_index_text=decision_index_text,
        )
        cls = verified["authority_class"]
        if cls not in AUTHORITY_CLASSES:
            cls = "UNKNOWN"
        # For decision/spec/contract docs, retain polarity cues in excerpt.
        if cls in STRONG_AUTHORITY_CLASSES or cls == "CHANGE_CONTEXT":
            excerpt, line_start, line_end = self._authority_excerpt(
                path=path, full_text=full_text, fallback=excerpt
            )
        excerpt = excerpt[:800]
        if not self._can_add_evidence(excerpt):
            return None
        if test_kind is None and cls == "TEST_EVIDENCE":
            test_kind = classify_test_kind(excerpt, path)
        item = EvidenceItem(
            evidence_id=self._next_id(id_prefix),
            authority_class=cls,
            authority_verified=bool(verified["authority_verified"]),
            authority_basis=str(verified["authority_basis"]),
            lifecycle_status=verified.get("lifecycle_status"),
            path=path,
            line_start=line_start,
            line_end=line_end,
            excerpt=excerpt,
            match_reason=match_reason,
            test_kind=test_kind,
        )
        self._evidence.append(item)
        self.budget.evidence_items += 1
        self.budget.excerpt_bytes += len(excerpt.encode("utf-8"))
        return item

    def exact_search(
        self,
        needle: str,
        *,
        intent_label: str,
        authority_hint: str | None = None,
        path_prefer: tuple[str, ...] = (),
        path_exclude: frozenset[str] | None = None,
    ) -> list[EvidenceItem]:
        """Exact-string search under budgets; returns newly added items."""
        if not needle or not needle.strip():
            return []
        if self.budget.intents_used >= MAX_SEARCH_INTENTS:
            self.budget.note_exhaustion("max_search_intents")
            return []
        self.budget.intents_used += 1
        found: list[EvidenceItem] = []
        candidates = 0
        exclude = path_exclude or frozenset()
        # Prefer stable paths first when available.
        preferred: list[Path] = []
        others: list[Path] = []
        for path in self.iter_regular_files():
            rel = self._rel_of(path)
            if rel in exclude:
                continue
            if any(rel.startswith(p) or p in rel for p in path_prefer):
                preferred.append(path)
            else:
                others.append(path)
        for path in preferred + others:
            if candidates >= MAX_CANDIDATE_FILES_PER_INTENT:
                self.budget.note_exhaustion("max_candidate_files_per_intent")
                break
            if self.budget.evidence_items >= MAX_EVIDENCE_ITEMS:
                break
            candidates += 1
            self.budget.candidates_scanned += 1
            text = self.read_text_file(path)
            if text is None:
                continue
            if needle not in text:
                continue
            rel = self._rel_of(path)
            lines = text.splitlines()
            hit_line = 1
            for i, line in enumerate(lines, start=1):
                if needle in line:
                    hit_line = i
                    break
            start = max(1, hit_line - 2)
            end = min(len(lines), hit_line + 2)
            excerpt = "\n".join(lines[start - 1 : end])
            item = self.add_evidence(
                authority_class=authority_hint,
                path=rel,
                line_start=start,
                line_end=end,
                excerpt=excerpt,
                match_reason=f"{intent_label}: exact match {needle!r}",
                full_text=text,
                decision_index_text=getattr(self, "_decision_index_text", None),
            )
            if item is not None:
                found.append(item)
        return found

    @property
    def evidence(self) -> list[EvidenceItem]:
        """Collected evidence items."""
        return list(self._evidence)


def parse_lifecycle_status(text: str) -> str | None:
    """Extract explicit lifecycle/status field from document text."""
    m = _STATUS_RE.search(text or "")
    if not m:
        return None
    return m.group(1).strip().lower()


def classify_path_authority(rel: str, excerpt: str = "") -> str:
    """Provisional class from path/content — never proves normative authority."""
    del excerpt  # path-only provisional; content used in verify_authority
    norm = rel.replace("\\", "/").lower()
    if any(norm.startswith(p) or f"/{p}" in f"/{norm}" for p in _CANONICAL_DECISIONS):
        return "ACCEPTED_DECISION"
    if "openspec/changes/" in norm and "/specs/" in norm:
        return "CHANGE_CONTEXT"
    if any(norm.startswith(p) or f"/{p}" in f"/{norm}" for p in _CANONICAL_CURRENT_SPECS):
        return "CURRENT_SPEC"
    if any(norm.startswith(p) or f"/{p}" in f"/{norm}" for p in _CANONICAL_CONTRACTS):
        return "CONTRACT"
    if norm.endswith(".md") and ("contract" in Path(norm).name or "policy" in Path(norm).name):
        return "CONTRACT"
    if "/tests/" in f"/{norm}" or norm.startswith("tests/") or "/test_" in norm:
        return "TEST_EVIDENCE"
    if "doto/" in norm or "worklog" in norm or "debt" in norm:
        return "BUG_DEBT_EVIDENCE"
    if norm.endswith(".py"):
        return "SOURCE_CODE"
    return "UNKNOWN"


def _index_mentions_decision(
    index_text: str | None, decision_rel: str
) -> str | None:
    """Return lifecycle status for decision from index when explicitly listed."""
    if not index_text:
        return None
    name = Path(decision_rel).name
    stem = Path(decision_rel).stem
    for line in index_text.splitlines():
        low = line.lower()
        if name.lower() not in low and stem.lower() not in low:
            continue
        # Prefer inline status tokens on the same line.
        for tok in ("accepted", "rejected", "superseded", "proposed", "draft"):
            if re.search(rf"\b{tok}\b", low):
                return tok
        m = _STATUS_RE.search(line)
        if m:
            return m.group(1).strip().lower()
    return None


def verify_authority(
    rel: str,
    text: str,
    *,
    provisional_class: str | None = None,
    decision_index_text: str | None = None,
) -> dict[str, Any]:
    """Prove or reject normative authority for a repository evidence item.

    Path location alone never sets ``authority_verified=true``.
    """
    provisional = provisional_class or classify_path_authority(rel, text)
    lifecycle = parse_lifecycle_status(text)
    norm = rel.replace("\\", "/").lower()

    # Decision documents.
    if provisional == "ACCEPTED_DECISION" or any(
        norm.startswith(p) for p in _CANONICAL_DECISIONS
    ):
        index_status = _index_mentions_decision(decision_index_text, rel)
        status = lifecycle
        if status is None and index_status is not None:
            status = index_status
        if status is None:
            return {
                "authority_class": "ACCEPTED_DECISION",
                "authority_verified": False,
                "authority_basis": "decision_status_unproven",
                "lifecycle_status": "unknown",
            }
        if status in _NON_ACCEPTED:
            return {
                "authority_class": "ACCEPTED_DECISION",
                "authority_verified": False,
                "authority_basis": f"decision_status_{status}",
                "lifecycle_status": status,
            }
        if status != "accepted":
            return {
                "authority_class": "ACCEPTED_DECISION",
                "authority_verified": False,
                "authority_basis": f"decision_status_{status}",
                "lifecycle_status": status,
            }
        # Accepted in document; if index contradicts, fail closed.
        if index_status is not None and index_status != "accepted":
            return {
                "authority_class": "ACCEPTED_DECISION",
                "authority_verified": False,
                "authority_basis": "decision_index_inconsistent",
                "lifecycle_status": status,
            }
        basis = "explicit_status_accepted"
        if index_status == "accepted":
            basis = "explicit_status_accepted+index_consistent"
        return {
            "authority_class": "ACCEPTED_DECISION",
            "authority_verified": True,
            "authority_basis": basis,
            "lifecycle_status": "accepted",
        }

    # Change-local specs are never CURRENT_SPEC.
    if "openspec/changes/" in norm and "/specs/" in norm:
        return {
            "authority_class": "CHANGE_CONTEXT",
            "authority_verified": False,
            "authority_basis": "change_local_spec_not_current",
            "lifecycle_status": lifecycle or "unknown",
        }

    # Canonical current specs.
    if provisional == "CURRENT_SPEC" or any(
        norm.startswith(p) for p in _CANONICAL_CURRENT_SPECS
    ):
        if not any(norm.startswith(p) for p in _CANONICAL_CURRENT_SPECS):
            return {
                "authority_class": "CURRENT_SPEC",
                "authority_verified": False,
                "authority_basis": "non_canonical_spec_path",
                "lifecycle_status": lifecycle,
            }
        if lifecycle in _NON_ACCEPTED:
            return {
                "authority_class": "CURRENT_SPEC",
                "authority_verified": False,
                "authority_basis": f"spec_status_{lifecycle}",
                "lifecycle_status": lifecycle,
            }
        # Normative current-spec location with no draft/rejected marker.
        if lifecycle in {None, "accepted", "active", "current"}:
            return {
                "authority_class": "CURRENT_SPEC",
                "authority_verified": True,
                "authority_basis": "canonical_current_spec_location",
                "lifecycle_status": lifecycle or "current",
            }
        return {
            "authority_class": "CURRENT_SPEC",
            "authority_verified": False,
            "authority_basis": f"spec_status_{lifecycle}",
            "lifecycle_status": lifecycle,
        }

    # CONTRACT: lifecycle vetoes first; only then canonical + normative marker.
    if provisional == "CONTRACT":
        under_canonical = any(norm.startswith(p) for p in _CANONICAL_CONTRACTS)
        # Explicit non-active lifecycle always vetoes — normative marker cannot override.
        if lifecycle is not None and lifecycle not in {"accepted", "active", "current"}:
            return {
                "authority_class": "CONTRACT",
                "authority_verified": False,
                "authority_basis": f"contract_lifecycle_{lifecycle}",
                "lifecycle_status": lifecycle,
            }
        normative_marker = bool(
            re.search(
                r"(?im)^\s*(?:contract_kind|normative)\s*[:=]\s*(?:normative|true|yes)\s*$",
                text,
            )
        )
        if under_canonical and normative_marker:
            return {
                "authority_class": "CONTRACT",
                "authority_verified": True,
                "authority_basis": "canonical_contract_normative_marker",
                "lifecycle_status": lifecycle or "current",
            }
        return {
            "authority_class": "CONTRACT",
            "authority_verified": False,
            "authority_basis": (
                "pathname_contract_unverified"
                if not under_canonical
                else "contract_marker_missing"
            ),
            "lifecycle_status": lifecycle,
        }

    # API_INVARIANT: explicit invariant material only.
    if re.search(r"(?im)\b(?:@invariant|api_invariant|INVARIANT:)\b", text):
        return {
            "authority_class": "API_INVARIANT",
            "authority_verified": True,
            "authority_basis": "explicit_api_invariant_marker",
            "lifecycle_status": None,
        }

    # Non-strong classes: never verified as normative authority.
    cls = provisional if provisional in AUTHORITY_CLASSES else "UNKNOWN"
    return {
        "authority_class": cls,
        "authority_verified": False,
        "authority_basis": "non_strong_or_unproven",
        "lifecycle_status": lifecycle,
    }


def classify_test_kind(excerpt: str, rel: str) -> str:
    """Classify test evidence; UNKNOWN when not provable."""
    low = excerpt.lower()
    if "characterization" in low or "characterise" in low or "snapshot" in low:
        return "characterization"
    if any(
        tok in low
        for tok in (
            "assert ",
            "pytest.raises",
            "must ",
            "shall ",
            "contract",
            "invariant",
        )
    ):
        # Presence of assert alone is weak — mark UNKNOWN unless contract language.
        if "contract" in low or "invariant" in low or "shall " in low or "must " in low:
            return "contract"
        return "UNKNOWN"
    if "integration" in low or "regression" in rel.lower():
        return "integration"
    return "UNKNOWN"


def extract_changed_symbols(base: str | None, ours: str | None, theirs: str | None) -> list[str]:
    """Extract def/class names that differ across sides."""
    def names(text: str | None) -> set[str]:
        if not text:
            return set()
        out: set[str] = set()
        for m in _DEF_RE.finditer(text):
            out.add(m.group(1) or m.group(2))
        return out

    nb, no, nt = names(base), names(ours), names(theirs)
    changed = sorted((no | nt) - nb) or sorted(no ^ nt) or sorted(no | nt)
    # Also catch assignment-like identifiers used in conflict markers style.
    for text in (ours, theirs):
        if not text:
            continue
        for m in re.finditer(r"\bread_only\s*=\s*(True|False)\b", text):
            if "read_only" not in changed:
                changed.append("read_only")
    return changed[:12]


def extract_imports(text: str | None) -> list[str]:
    """Return import module/name strings via AST when parseable."""
    if not text:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.append(node.module)
    return mods[:20]


def _same_file_context(text: str | None, symbols: list[str]) -> dict[str, Any]:
    """Collect nearby definitions/imports from one side's text."""
    if not text:
        return {"imports": [], "definitions": [], "nearby": []}
    imports = extract_imports(text)
    defs = []
    nearby = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _DEF_RE.match(line)
        if m:
            name = m.group(1) or m.group(2)
            defs.append({"name": name, "line": i + 1})
            if name in symbols:
                start = max(0, i - 3)
                end = min(len(lines), i + 8)
                nearby.append(
                    {
                        "name": name,
                        "line_start": start + 1,
                        "line_end": end,
                        "excerpt": "\n".join(lines[start:end]),
                    }
                )
    return {"imports": imports, "definitions": defs[:30], "nearby": nearby[:8]}


def collect_conflict_context(
    repo_root: Path,
    *,
    conflict_path: str,
    operation: str,
    base_text: str | None,
    ours_text: str | None,
    theirs_text: str | None,
    stage_oids: dict[str, str | None],
) -> dict[str, Any]:
    """Build a bounded structured conflict-context packet (evidence layer)."""
    reader = BoundedContextReader(repo_root)
    path_norm = conflict_path.replace("\\", "/")
    symbols = extract_changed_symbols(base_text, ours_text, theirs_text)
    gaps: list[str] = []

    # Optional decision index — one bounded read for consistency checks.
    index_path = reader.repo_root / _DECISION_INDEX_REL
    decision_index_text: str | None = None
    if index_path.is_file() and not index_path.is_symlink():
        decision_index_text = reader.read_text_file(index_path)
    reader._decision_index_text = decision_index_text  # type: ignore[attr-defined]

    # A. Conflict blobs summary (inline, not file reads).
    conflict_blobs = {
        "path": path_norm,
        "operation": operation,
        "stage_oids": stage_oids,
        "changed_symbols": symbols,
        "base_present": base_text is not None,
        "ours_present": ours_text is not None,
        "theirs_present": theirs_text is not None,
    }

    # B. Same-file context from stage texts (no disk write).
    same_file = {
        "ours": _same_file_context(ours_text, symbols),
        "theirs": _same_file_context(theirs_text, symbols),
    }

    # Prefer reading sibling files in the same directory (bounded).
    conflict_abs = reader.repo_root / path_norm
    sibling_dir = conflict_abs.parent if conflict_abs.parent.exists() else reader.repo_root
    sib_scanned = 0
    for sib in sorted(sibling_dir.glob("*.py")):
        if sib_scanned >= MAX_CANDIDATE_FILES_PER_INTENT:
            reader.budget.note_exhaustion("max_candidate_files_per_intent")
            break
        sib_scanned += 1
        reader.budget.candidates_scanned += 1
        if sib.is_symlink():
            continue
        if reader._rel_of(sib) == path_norm:
            continue
        text = reader.read_text_file(sib)
        if text is None:
            continue
        hit = False
        reason = "sibling module in same package"
        for sym in symbols:
            if sym and sym in text:
                hit = True
                reason = f"sibling references changed symbol {sym!r}"
                break
        if "read_only" in (ours_text or "") + (theirs_text or "") and "read_only" in text:
            hit = True
            reason = "sibling shares read_only API usage"
        if not hit and len(reader.evidence) < 3:
            hit = True
            reason = "sibling implementation in same directory"
        if hit:
            lines = text.splitlines()
            reader.add_evidence(
                authority_class="SIBLING_IMPLEMENTATION",
                path=reader._rel_of(sib),
                line_start=1,
                line_end=min(12, len(lines)),
                excerpt="\n".join(lines[:12]),
                match_reason=reason,
                full_text=text,
                id_prefix="SIB",
                decision_index_text=decision_index_text,
            )
        if reader.budget.evidence_items >= 5:
            break

    # C/D/E/F. Bounded searches only — no separate unbounded rglob.
    intents: list[tuple[str, str, str | None, tuple[str, ...]]] = []
    for sym in symbols[:2]:
        intents.append(
            (
                sym,
                f"usages of {sym}",
                None,
                ("tests/", "openspec/decisions/", "openspec/specs/", "app/", "handlers/"),
            )
        )
    if len(intents) < MAX_SEARCH_INTENTS:
        intents.append(
            (
                path_norm.split("/")[-1].removesuffix(".py"),
                "tests/docs referencing conflict basename",
                None,
                ("tests/", "openspec/"),
            )
        )
    if len(intents) < MAX_SEARCH_INTENTS:
        token = None
        for side in (ours_text, theirs_text):
            if side and "read_only" in side:
                token = "read_only"
                break
        if token is None:
            token = "existing-users-only"
        if all(t[0] != token for t in intents):
            intents.append(
                (
                    token,
                    "decisions/specs mentioning conflict token",
                    None,
                    ("openspec/decisions/", "openspec/specs/", "openspec/contracts/"),
                )
            )

    for needle, label, auth, prefer in intents[:MAX_SEARCH_INTENTS]:
        if reader.budget.intents_used >= MAX_SEARCH_INTENTS:
            break
        reader.exact_search(
            needle,
            intent_label=label,
            authority_hint=auth,
            path_prefer=prefer,
            path_exclude=frozenset({path_norm}),
        )

    # G. Evidence gaps.
    classes_present = {e.authority_class for e in reader.evidence}
    verified_strong = [
        e
        for e in reader.evidence
        if e.authority_verified and e.authority_class in STRONG_AUTHORITY_CLASSES
    ]
    if "SIBLING_IMPLEMENTATION" not in classes_present:
        gaps.append("SIBLING_IMPLEMENTATION not found within budget")
    if "TEST_EVIDENCE" not in classes_present:
        gaps.append("TEST_EVIDENCE not found within budget")
    if not verified_strong:
        gaps.append(
            "No verified strong authority "
            "(ACCEPTED_DECISION/CURRENT_SPEC/CONTRACT/API_INVARIANT) within budget"
        )
    if not symbols:
        gaps.append("No changed symbols extracted from stage blobs")
    for reason in reader.budget.exhausted:
        gaps.append(f"EVIDENCE_GAP budget: {reason}")

    return {
        "schema": CONTEXT_PACKET_SCHEMA,
        "conflict_blobs": conflict_blobs,
        "same_file_context": same_file,
        "evidence": [e.as_dict() for e in reader.evidence],
        "evidence_gaps": gaps,
        "search_budgets": {
            "max_search_intents": MAX_SEARCH_INTENTS,
            "max_candidate_files_per_intent": MAX_CANDIDATE_FILES_PER_INTENT,
            "max_evidence_items": MAX_EVIDENCE_ITEMS,
            "max_excerpt_bytes_total": MAX_EXCERPT_BYTES_TOTAL,
            "max_bytes_read": MAX_BYTES_READ,
            "intents_used": reader.budget.intents_used,
            "candidates_scanned": reader.budget.candidates_scanned,
            "evidence_items": reader.budget.evidence_items,
            "excerpt_bytes": reader.budget.excerpt_bytes,
            "files_enumerated": reader.budget.files_enumerated,
            "bytes_read": reader.budget.bytes_read,
            "exhausted": list(reader.budget.exhausted),
        },
        "reader_contract": {
            "subprocess": False,
            "writes": False,
            "symlink_policy": "STOP",
            "binary_oversized_policy": "skip",
            "path_escape_policy": "STOP",
            "authority_path_alone": False,
            "recommendation_requires_authority_verified": True,
        },
    }
