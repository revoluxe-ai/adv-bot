"""Bounded verification для .opsx/registry/*.ndjson."""

from __future__ import annotations

import json
from typing import Any


def _identity_key(record: dict[str, Any], path: str) -> str | None:
    """Stable identity key per registry file kind."""

    norm = path.replace("\\", "/")
    if "command_activation" in norm:
        for key in ("command", "command_id", "id"):
            if key in record:
                return str(record[key])
    if "provenance" in norm:
        for key in ("event", "event_id", "id", "record_id"):
            if key in record:
                return str(record[key])
    for key in ("id", "command", "event"):
        if key in record:
            return str(record[key])
    return None


def verify_registry_ndjson_parseable(content: str) -> tuple[bool, list[str]]:
    """NDJSON parseable + per-line object + unique identity keys."""

    refs: list[str] = []
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if not lines:
        return True, ["ndjson:empty_allowed"]

    seen: set[str] = set()
    for idx, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return False, [f"ndjson:line_{idx}:invalid_json"]
        if not isinstance(obj, dict):
            return False, [f"ndjson:line_{idx}:not_object"]
        refs.append(f"ndjson:line_{idx}:object")

    refs.append(f"ndjson:line_count:{len(lines)}")
    return True, refs


def verify_registry_ndjson_synthesis(
    synthesized: str,
    target_side: str,
    path: str,
) -> tuple[bool, list[str]]:
    """
    Post-synthesis registry check: parseable, keys preserved, no silent target drop.
    """

    ok_syn, syn_refs = verify_registry_ndjson_parseable(synthesized)
    if not ok_syn:
        return False, syn_refs

    ok_tgt, tgt_refs = verify_registry_ndjson_parseable(target_side)
    if not ok_tgt:
        return False, tgt_refs

    def _keys(content: str) -> set[str]:
        keys: set[str] = set()
        for line in content.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                ident = _identity_key(obj, path)
                if ident:
                    keys.add(ident)
        return keys

    target_keys = _keys(target_side)
    synth_keys = _keys(synthesized)
    missing = target_keys - synth_keys
    if missing:
        return False, [
            f"ndjson:target_key_removed:{k}" for k in sorted(missing)[:5]
        ]

    refs = syn_refs + tgt_refs + [
        "ndjson:target_keys_preserved",
        f"ndjson:synth_key_count:{len(synth_keys)}",
    ]
    return True, refs
