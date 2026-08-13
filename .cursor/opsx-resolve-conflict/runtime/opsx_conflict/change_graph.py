"""Git-grounded logical change graph (RC04-H06)."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any

from .errors import StopRequired


@dataclass(frozen=True)
class ContractView:
    definitions: frozenset[str]
    signatures: frozenset[str]
    calls: frozenset[str]
    imports: frozenset[str]
    parse_ok: bool


def extract_python_contracts(text: str) -> ContractView:
    """Extract defs/signatures/calls/imports; parse failure is explicit."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ContractView(frozenset(), frozenset(), frozenset(), frozenset(), False)

    definitions: set[str] = set()
    signatures: set[str] = set()
    calls: set[str] = set()
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.add(node.name)
            args = [a.arg for a in node.args.args]
            signatures.add(f"{node.name}({','.join(args)})")
        elif isinstance(node, ast.ClassDef):
            definitions.add(node.name)
            signatures.add(f"class:{node.name}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    # Guard heuristics
    if re.search(r"\braise\b|\breturn\b|\bif\b", text):
        definitions.add("__has_control_flow__")

    return ContractView(
        frozenset(definitions),
        frozenset(signatures),
        frozenset(calls),
        frozenset(imports),
        True,
    )


def detect_logical_conflict_candidates(
    *,
    path: str,
    base_text: str | None,
    source_text: str | None,
    target_text: str | None,
) -> list[dict[str, Any]]:
    """
    Compare stage texts. Unsupported/non-python → unresolved candidate.
    SyntaxError → STOP/unresolved, never empty silent success.
    """
    if not path.endswith(".py"):
        return [
            {
                "path": path,
                "kind": "non_python_unresolved",
                "status": "UNRESOLVED_CANDIDATE",
            }
        ]

    views = {
        "base": extract_python_contracts(base_text or ""),
        "source": extract_python_contracts(source_text or ""),
        "target": extract_python_contracts(target_text or ""),
    }
    for side, view in views.items():
        if (base_text if side == "base" else source_text if side == "source" else target_text) and not view.parse_ok:
            raise StopRequired(
                "LOGICAL_GRAPH_PARSE_FAILED",
                {"path": path, "side": side},
            )

    findings: list[dict[str, Any]] = []
    if views["source"].signatures != views["target"].signatures:
        findings.append(
            {
                "path": path,
                "kind": "signature_divergence",
                "source_only": sorted(views["source"].signatures - views["target"].signatures),
                "target_only": sorted(views["target"].signatures - views["source"].signatures),
            }
        )
    removed = views["source"].definitions - views["target"].definitions
    if removed:
        findings.append({"path": path, "kind": "definition_removed", "names": sorted(removed)})
    # Guard removal: control-flow marker lost on one side
    if "__has_control_flow__" in views["source"].definitions and "__has_control_flow__" not in views[
        "target"
    ].definitions:
        findings.append({"path": path, "kind": "guard_or_control_removed"})
    return findings
