#!/usr/bin/env python3
"""
sync-cursor-models.py — helper for /opsx-meta-sync-models.

Читает materialized MODEL_REGISTRY.json или обновляет через Cursor API
`GET https://api.cursor.com/v1/models` (httpx из Poetry deps; CURSOR_API_KEY).
Не требует пакет cursor-sdk (конфликт httpx с adv-bot).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_DIR = REPO_ROOT / ".cursor" / "pipeline" / "shared"
REGISTRY_PATH = SHARED_DIR / "MODEL_REGISTRY.json"
META_PATH = SHARED_DIR / "MODEL_REGISTRY.meta.json"
SCHEMA_PATH = SHARED_DIR / "MODEL_REGISTRY.schema.json"

LAST_FETCH_SOURCE = "cursor_api.GET.v1.models"

PSEUDO_MODELS: list[dict[str, str]] = [
    {
        "slug": "inherit",
        "kind": "pseudo",
        "description": "Parent chat agent model (Task model: inherit)",
    },
    {
        "slug": "auto",
        "kind": "pseudo",
        "description": "Explicit platform Auto (not silent default)",
    },
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _slug_is_fast(slug: str) -> bool:
    lowered = slug.lower()
    return lowered.endswith("-fast") or "[fast=" in lowered or "fast" in lowered.split("-")


def _variant_group(slug: str) -> str:
    for suffix in ("-fast", "-high", "-medium", "-low"):
        if slug.endswith(suffix):
            return slug[: -len(suffix)]
    return slug.split("[", 1)[0]


def _normalize_catalog_item(item: dict[str, Any]) -> dict[str, Any]:
    """Нормализует элемент ответа GET /v1/models."""
    slug = str(item.get("id") or item.get("slug") or "")
    if not slug:
        return {}

    return {
        "slug": slug,
        "display_name": str(item.get("displayName") or item.get("display_name") or slug),
        "description": item.get("description"),
        "aliases": list(item.get("aliases") or []),
        "parameters": item.get("parameters") or [],
        "variants": item.get("variants") or [],
        "variant_group": _variant_group(slug),
        "is_fast_variant": _slug_is_fast(slug),
    }


def _variant_summary(model: dict[str, Any]) -> str:
    parts: list[str] = []
    for variant in model.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        params = variant.get("params") or []
        param_bits = [
            f"{p.get('id')}={p.get('value')}"
            for p in params
            if isinstance(p, dict) and p.get("id")
        ]
        label = variant.get("displayName") or variant.get("description") or "variant"
        default = " (default)" if variant.get("isDefault") else ""
        parts.append(f"{label}{default}: {', '.join(param_bits) or 'no params'}")
    return "; ".join(parts) if parts else "—"


def _fetch_via_httpx(api_key: str) -> dict[str, Any]:
    import httpx

    url = "https://api.cursor.com/v1/models"
    timeout = httpx.Timeout(60.0)
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, auth=(api_key, ""))
        if resp.status_code == 401:
            resp = client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if resp.status_code >= 400:
            snippet = resp.text[:300].replace("\n", " ")
            raise RuntimeError(f"HTTP {resp.status_code}: {snippet}")
        return resp.json()


def _fetch_via_cursor_sdk(api_key: str) -> list[Any]:
    from cursor_sdk import Cursor  # type: ignore[import-untyped]

    os.environ.setdefault("CURSOR_API_KEY", api_key)
    return list(Cursor.models.list())


def fetch_live_models() -> list[dict[str, Any]]:
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key or not api_key.strip():
        print("BLOCKED_MISSING_CREDENTIAL: set CURSOR_API_KEY", file=sys.stderr)
        sys.exit(3)

    api_key = api_key.strip()
    source = "cursor_api.GET.v1.models"
    raw_items: list[Any] = []

    try:
        import httpx  # noqa: F401 — capability probe
    except ImportError:
        print("BLOCKED_MISSING_CAPABILITY: httpx not available in environment", file=sys.stderr)
        sys.exit(2)

    try:
        payload = _fetch_via_httpx(api_key)
        raw_items = payload.get("items") or payload.get("models") or []
    except Exception as httpx_exc:  # noqa: BLE001
        try:
            raw_items = _fetch_via_cursor_sdk(api_key)
            source = "cursor_sdk.models.list"
        except ImportError:
            print(f"BLOCKED_API_ERROR: {httpx_exc}", file=sys.stderr)
            sys.exit(4)
        except Exception as sdk_exc:  # noqa: BLE001
            print(f"BLOCKED_API_ERROR: {httpx_exc}; sdk: {sdk_exc}", file=sys.stderr)
            sys.exit(4)

    models: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, dict):
            normalized = _normalize_catalog_item(item)
        else:
            normalized = _normalize_catalog_item({"id": str(item)})
        if normalized:
            models.append(normalized)

    models.sort(key=lambda m: m["slug"])
    global LAST_FETCH_SOURCE
    LAST_FETCH_SOURCE = source
    return models


def build_registry(models: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "synced_at": _utc_now_iso(),
        "source": LAST_FETCH_SOURCE,
        "pseudo_models": PSEUDO_MODELS,
        "models": models,
    }


def diff_slugs(
    old: dict[str, Any] | None, new: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    old_map = {m["slug"]: m for m in (old or {}).get("models", [])}
    new_map = {m["slug"]: m for m in new.get("models", [])}
    old_slugs = set(old_map)
    new_slugs = set(new_map)
    added = sorted(new_slugs - old_slugs)
    removed = sorted(old_slugs - new_slugs)
    changed = sorted(
        s
        for s in old_slugs & new_slugs
        if json.dumps(old_map[s], sort_keys=True) != json.dumps(new_map[s], sort_keys=True)
    )
    return added, removed, changed


def format_table(registry: dict[str, Any]) -> str:
    lines = [
        "| slug | display | fast? | variants (params) | aliases |",
        "|------|---------|-------|-------------------|---------|",
    ]
    for pseudo in registry.get("pseudo_models", []):
        lines.append(
            f"| `{pseudo['slug']}` | {pseudo.get('description', '')} | pseudo | — | — |"
        )
    for model in registry.get("models", []):
        fast = "yes" if model.get("is_fast_variant") else "no"
        display = model.get("display_name", "")
        variants = _variant_summary(model)
        aliases = ", ".join(model.get("aliases") or []) or "—"
        lines.append(f"| `{model['slug']}` | {display} | {fast} | {variants} | {aliases} |")
    return "\n".join(lines)


def cmd_show() -> int:
    if not REGISTRY_PATH.is_file():
        print("STATUS: BLOCKED_NO_REGISTRY")
        print(f"REGISTRY_PATH: {REGISTRY_PATH}")
        print("NEXT_ACTION: /opsx-meta-sync-models UPDATE GO")
        return 1

    registry = _load_json(REGISTRY_PATH)
    meta: dict[str, Any] = {}
    if META_PATH.is_file():
        meta = _load_json(META_PATH)

    print("STATUS: SHOWN")
    print(f"REGISTRY_PATH: {REGISTRY_PATH}")
    print(f"SYNCED_AT: {registry.get('synced_at', 'unknown')}")
    print(f"SOURCE: {registry.get('source', 'unknown')}")
    print(f"MODEL_COUNT: {len(registry.get('models', []))}")
    if meta.get("stale_warning"):
        print(f"STALE_WARNING: {meta.get('stale_warning')}")
    print()
    print(format_table(registry))
    return 0


def cmd_update(write: bool) -> int:
    live_models = fetch_live_models()
    new_registry = build_registry(live_models)

    old_registry: dict[str, Any] | None = None
    if REGISTRY_PATH.is_file():
        old_registry = _load_json(REGISTRY_PATH)

    added, removed, changed = diff_slugs(old_registry, new_registry)

    print("STATUS: PLAN_READY" if not write else "SYNCED")
    print(f"REGISTRY_PATH: {REGISTRY_PATH}")
    print(f"SYNCED_AT: {new_registry['synced_at']}")
    print(f"SOURCE: {new_registry['source']}")
    print(f"MODEL_COUNT: {len(new_registry['models'])}")
    print(f"ADDED: {', '.join(added) if added else 'none'}")
    print(f"REMOVED: {', '.join(removed) if removed else 'none'}")
    print(f"CHANGED: {', '.join(changed) if changed else 'none'}")
    print()
    print(format_table(new_registry))

    if write:
        _write_json(REGISTRY_PATH, new_registry)
        _write_json(
            META_PATH,
            {
                "schema_version": 1,
                "synced_at": new_registry["synced_at"],
                "source": new_registry["source"],
                "model_count": len(new_registry["models"]),
                "registry_path": str(REGISTRY_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                "schema_path": str(SCHEMA_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            },
        )
        print()
        print("WRITE: performed")
    else:
        print()
        print("WRITE: not_performed (pass --write or use UPDATE GO)")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="OPSX Cursor model registry helper")
    parser.add_argument(
        "mode",
        choices=("show", "update"),
        help="show = read materialized registry; update = live fetch",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="On update: materialize MODEL_REGISTRY.json",
    )
    args = parser.parse_args()

    if args.mode == "show":
        return cmd_show()
    return cmd_update(write=args.write)


if __name__ == "__main__":
    sys.exit(main())
