"""Строгая authority evaluation для AI_SEMANTIC."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from opsx_conflict.models import AuthorityLane, PartitionedPath

_AUTHORITY_MARKER = re.compile(r"^#\s*OPSX_AUTHORITY:\s*(\S+)", re.MULTILINE)
_BUSINESS_CHOICE = re.compile(r"^#\s*BUSINESS_CHOICE:\s*(.+)$", re.MULTILINE)
_ARCH_CHOICE = re.compile(r"^#\s*ARCHITECTURE_CHOICE:\s*(.+)$", re.MULTILINE)
_DEF_RE = re.compile(r"^def\s+(\w+)", re.MULTILINE)
_CALL_RE = re.compile(r"\b(\w+)\s*\(")


@dataclass
class SemanticAuthorityResult:
    """Результат проверки AI_SEMANTIC authority."""

    allowed: bool
    authority_known: bool
    side_a_intent_evidenced: bool
    side_b_intent_evidenced: bool
    intents_compatible: bool
    invariants_preserved: bool
    no_new_decision: bool
    bounded_verification_available: bool
    authority_refs: list[str] = field(default_factory=list)
    side_a_intent_refs: list[str] = field(default_factory=list)
    side_b_intent_refs: list[str] = field(default_factory=list)
    preserved_invariants: list[str] = field(default_factory=list)
    reason_not_new_decision: str = ""
    verification_requirements: list[str] = field(default_factory=list)
    downgrade_reason: str = ""


def _extract_intent_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return lines


def _authority_from_markers(text: str) -> list[str]:
    return _AUTHORITY_MARKER.findall(text or "")


def _business_choices(text: str) -> list[str]:
    return [m.strip() for m in _BUSINESS_CHOICE.findall(text or "")]


def _arch_choices(text: str) -> list[str]:
    return [m.strip() for m in _ARCH_CHOICE.findall(text or "")]


def evaluate_ai_semantic_authority(
    part: PartitionedPath,
    side_a: str | None,
    side_b: str | None,
    base: str | None,
    repo_root: Path,
) -> SemanticAuthorityResult:
    """Все условия AI_SEMANTIC должны быть доказаны."""

    refs: list[str] = []
    authority_known = False
    external_refs: list[str] = []

    if part.inventory_class == "A_IN_SCOPE" and part.lane == AuthorityLane.PROCESS:
        sources = repo_root / ".opsx" / "sources.yaml"
        if sources.is_file():
            authority_known = True
            external_refs.append("sources.yaml:allowlist:A_IN_SCOPE")

    # Markers in conflicted file content are hints only — never self-authorize
    combined = (base or "") + (side_a or "") + (side_b or "")
    marker_hints = _authority_from_markers(combined)
    refs.extend(external_refs)
    if marker_hints and authority_known:
        refs.extend([f"marker_hint:OPSX_AUTHORITY:{m}" for m in marker_hints])

    side_a_lines = _extract_intent_lines(side_a or "")
    side_b_lines = _extract_intent_lines(side_b or "")
    side_a_intent = len(side_a_lines) > 0
    side_b_intent = len(side_b_lines) > 0
    side_a_refs = [f"side_a_line:{i}" for i in range(len(side_a_lines))]
    side_b_refs = [f"side_b_line:{i}" for i in range(len(side_b_lines))]

    intents_compatible = True
    if side_a and side_b and side_a != side_b:
        a_set = set(side_a_lines)
        b_set = set(side_b_lines)
        if a_set and b_set and not (a_set & b_set):
            if not authority_known:
                intents_compatible = False
        elif a_set and b_set:
            # overlapping content — compatible for synthesis under authority
            pass

    biz_a = _business_choices(side_a or "")
    biz_b = _business_choices(side_b or "")
    arch_a = _arch_choices(side_a or "")
    arch_b = _arch_choices(side_b or "")
    no_new_decision = True
    if biz_a and biz_b and set(biz_a) != set(biz_b):
        no_new_decision = False
    if arch_a and arch_b and set(arch_a) != set(arch_b):
        no_new_decision = False

    invariants = list(marker_hints) if authority_known else []
    invariants_preserved = authority_known and no_new_decision

    bounded_verification = path_verification_available(part.path)

    allowed = (
        authority_known
        and side_a_intent
        and side_b_intent
        and intents_compatible
        and invariants_preserved
        and no_new_decision
        and bounded_verification
    )

    downgrade = ""
    if not authority_known:
        downgrade = "authority_missing"
    elif not side_a_intent or not side_b_intent:
        downgrade = "intent_not_evidenced"
    elif not intents_compatible:
        downgrade = "intents_incompatible"
    elif not no_new_decision:
        downgrade = "new_business_or_architecture_decision"
    elif not bounded_verification:
        downgrade = "bounded_verification_unavailable"

    reason_not_new = (
        "union_preserves_both_side_unique_lines_under_known_authority"
        if allowed
        else downgrade
    )

    ver_req = []
    if part.path.endswith(".py"):
        ver_req.append("resolution:python_syntax_ok")
    ver_req.append("candidate:bound:post_resolution")

    return SemanticAuthorityResult(
        allowed=allowed,
        authority_known=authority_known,
        side_a_intent_evidenced=side_a_intent,
        side_b_intent_evidenced=side_b_intent,
        intents_compatible=intents_compatible,
        invariants_preserved=invariants_preserved,
        no_new_decision=no_new_decision,
        bounded_verification_available=bounded_verification,
        authority_refs=refs,
        side_a_intent_refs=side_a_refs,
        side_b_intent_refs=side_b_refs,
        preserved_invariants=invariants,
        reason_not_new_decision=reason_not_new,
        verification_requirements=ver_req,
        downgrade_reason=downgrade,
    )


def path_verification_available(path: str) -> bool:
    """Bounded verification доступна для path type."""

    norm = path.replace("\\", "/")
    if norm.endswith(
        (".py", ".md", ".mdc", ".yaml", ".yml", ".json", ".txt", ".ndjson")
    ):
        return True
    return False
