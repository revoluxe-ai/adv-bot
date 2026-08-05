"""
Offline API Master map: path × method × family из локальных vN swagger.

Capability `wb-api-master-map` / INC-RO-03. Без сети, без codegen, без WB API.
Ownership: openspec/.../wb-api-master-local-swagger-map/decision.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast

import yaml

SCHEMA_VERSION = "wb-api-master-map/v1"
HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
)
_VERSION_DIR_RE = re.compile(r"^v(\d+)$")

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED_ROOT = REPO_ROOT / "app" / "core" / "mp" / "wb" / "api" / "generated"


@dataclass(frozen=True, order=True)
class MapEntry:
    """Одна операция allowlist: path × method × family из локального swagger."""

    family: str
    path: str
    method: str


@dataclass(frozen=True)
class SourceGap:
    """Честный gap по источнику family без fabricated entries."""

    family: str
    reason: str


@dataclass(frozen=True)
class SourceMeta:
    """Метаданные успешно прочитанного локального swagger источника."""

    family: str
    version: int
    yaml_basename: str
    yaml_path: str


@dataclass
class MapBuildResult:
    """Результат offline сборки inventory map."""

    schema_version: str
    sources: list[SourceMeta] = field(default_factory=list[SourceMeta])
    entries: list[MapEntry] = field(default_factory=list[MapEntry])
    gaps: list[SourceGap] = field(default_factory=list[SourceGap])

    @property
    def ok(self) -> bool:
        """True только если есть хотя бы одна entry из swagger (не silent empty success)."""
        return bool(self.entries)


def _as_str_keyed_dict(value: object) -> dict[str, Any] | None:
    """Привести unknown mapping к dict[str, Any] для strict typing."""
    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    return {str(key): item for key, item in raw.items()}


def parse_openapi_paths(document: Mapping[str, Any], family: str) -> list[MapEntry]:
    """
    Извлечь path×method из OpenAPI document для данной family.

    Spec: Offline API Master map / No invent URL / Declared methods inventoried.
    Args:
        document: уже загруженный OpenAPI mapping
        family: identity источника (каталог/swagger target)
    Returns:
        Список MapEntry только из объявленных paths/methods
    """
    paths = _as_str_keyed_dict(document.get("paths"))
    if paths is None:
        return []

    entries: list[MapEntry] = []
    for path_key, path_item_raw in paths.items():
        path_item = _as_str_keyed_dict(path_item_raw)
        if path_item is None:
            continue
        if "$ref" in path_item and len(path_item) == 1:
            # MVP: не резолвим $ref — пропускаем без invent
            continue
        for method_key, operation in path_item.items():
            method_l = method_key.lower()
            if method_l not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            entries.append(
                MapEntry(family=family, path=path_key, method=method_l.upper())
            )
    return sorted(set(entries))


def load_and_parse_yaml(yaml_path: Path, family: str) -> list[MapEntry]:
    """
    Прочитать локальный YAML и извлечь MapEntry.

    Raises:
        OSError / yaml.YAMLError / ValueError при нечитаемом или не-mapping документе
    """
    raw = yaml_path.read_text(encoding="utf-8")
    loaded: object = yaml.safe_load(raw)
    document = _as_str_keyed_dict(loaded)
    if document is None:
        raise ValueError(f"OpenAPI root must be a mapping: {yaml_path}")
    return parse_openapi_paths(document, family)


def list_version_dirs(family_root: Path) -> list[tuple[int, Path]]:
    """Вернуть отсортированные (version, path) для каталогов vN под family_root."""
    if not family_root.is_dir():
        return []
    found: list[tuple[int, Path]] = []
    for child in family_root.iterdir():
        if not child.is_dir():
            continue
        match = _VERSION_DIR_RE.match(child.name)
        if match:
            found.append((int(match.group(1)), child))
    return sorted(found, key=lambda item: item[0])


def find_swagger_yamls(version_dir: Path) -> list[Path]:
    """Найти *.yaml / *.yml в version_dir/swagger/."""
    swagger_dir = version_dir / "swagger"
    if not swagger_dir.is_dir():
        return []
    files = sorted(
        [
            p
            for p in swagger_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}
        ],
        key=lambda p: p.name,
    )
    return files


def resolve_latest_source(
    family: str, family_root: Path, force_version: int | None = None
) -> tuple[SourceMeta, Path] | SourceGap:
    """
    Выбрать latest (или force) vN с swagger YAML для family.

    Returns:
        (SourceMeta, yaml_path) или SourceGap
    """
    versions = list_version_dirs(family_root)
    if not versions:
        return SourceGap(family=family, reason="no_version_dirs")

    if force_version is not None:
        selected = next((v for v in versions if v[0] == force_version), None)
        if selected is None:
            return SourceGap(
                family=family, reason=f"version_not_found:v{force_version}"
            )
    else:
        # latest numeric vN that has swagger yaml
        selected = None
        for version, path in reversed(versions):
            yamls = find_swagger_yamls(path)
            if yamls:
                selected = (version, path)
                break
        if selected is None:
            return SourceGap(family=family, reason="no_swagger_yaml")

    version, version_dir = selected
    yamls = find_swagger_yamls(version_dir)
    if not yamls:
        return SourceGap(family=family, reason="no_swagger_yaml")

    # Один primary yaml на version (первый по имени; обычно один файл)
    yaml_path = yamls[0]
    meta = SourceMeta(
        family=family,
        version=version,
        yaml_basename=yaml_path.name,
        yaml_path=str(yaml_path.resolve()),
    )
    return meta, yaml_path


def default_family_roots(
    generated_root: Path | None = None,
) -> dict[str, Path]:
    """
    Known family roots: каталоги под generated/, совпадающие с SWAGGER_TARGETS
    или любой sibling с vN/swagger (discover).

    Не вызывает download/codegen.
    """
    root = generated_root if generated_root is not None else GENERATED_ROOT
    if not root.is_dir():
        return {}

    # Prefer keys from generate_wb_api_client SWAGGER_TARGETS without network
    preferred: list[str] = []
    try:
        from generate_wb_api_client import SWAGGER_TARGETS  # type: ignore[import-not-found]

        preferred = list(SWAGGER_TARGETS.keys())
    except Exception:
        preferred = ["promotion", "products", "reports"]

    roots: dict[str, Path] = {}
    for name in preferred:
        candidate = root / name
        if candidate.is_dir():
            roots[name] = candidate

    # Discover additional family dirs that look like generated trees
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in roots:
            continue
        if list_version_dirs(child):
            roots[child.name] = child
    return roots


def build_map_from_yaml_paths(
    sources: Sequence[tuple[str, Path]],
) -> MapBuildResult:
    """
    Собрать map из явных (family, yaml_path).

    Spec: Honest gaps; Map does not authorize WB calls.
    """
    result = MapBuildResult(schema_version=SCHEMA_VERSION)
    all_entries: list[MapEntry] = []

    for family, yaml_path in sources:
        if not yaml_path.is_file():
            result.gaps.append(
                SourceGap(family=family, reason=f"missing_file:{yaml_path}")
            )
            continue
        try:
            entries = load_and_parse_yaml(yaml_path, family)
        except (OSError, yaml.YAMLError, ValueError, UnicodeError) as exc:
            result.gaps.append(
                SourceGap(family=family, reason=f"parse_error:{type(exc).__name__}")
            )
            continue
        # version unknown for explicit path — use 0 sentinel in meta
        result.sources.append(
            SourceMeta(
                family=family,
                version=0,
                yaml_basename=yaml_path.name,
                yaml_path=str(yaml_path.resolve()),
            )
        )
        all_entries.extend(entries)

    result.entries = sorted(set(all_entries))
    return result


def build_map_from_family_roots(
    family_roots: Mapping[str, Path],
    *,
    force_version: int | None = None,
    families: Iterable[str] | None = None,
) -> MapBuildResult:
    """
    Сканировать family roots → latest vN swagger → inventory.

    Spec: Offline API Master map; Family bound to swagger source.
    """
    result = MapBuildResult(schema_version=SCHEMA_VERSION)
    all_entries: list[MapEntry] = []
    selected = (
        list(families)
        if families is not None
        else sorted(family_roots.keys())
    )

    for family in selected:
        root = family_roots.get(family)
        if root is None:
            result.gaps.append(SourceGap(family=family, reason="unknown_family"))
            continue
        resolved = resolve_latest_source(family, root, force_version=force_version)
        if isinstance(resolved, SourceGap):
            result.gaps.append(resolved)
            continue
        meta, yaml_path = resolved
        try:
            entries = load_and_parse_yaml(yaml_path, family)
        except (OSError, yaml.YAMLError, ValueError, UnicodeError) as exc:
            result.gaps.append(
                SourceGap(family=family, reason=f"parse_error:{type(exc).__name__}")
            )
            continue
        result.sources.append(meta)
        all_entries.extend(entries)

    result.entries = sorted(set(all_entries))
    return result


def inventory_to_dict(result: MapBuildResult) -> dict[str, Any]:
    """
    Детерминированный dict для JSON SoT (без generated_at).

    Spec: Deterministic inventory artifact.
    """
    return {
        "schema_version": result.schema_version,
        "sources": [asdict(s) for s in result.sources],
        "entries": [
            {"family": e.family, "path": e.path, "method": e.method}
            for e in result.entries
        ],
        "gaps": [asdict(g) for g in result.gaps],
    }


def emit_json(result: MapBuildResult) -> str:
    """Сериализовать inventory в стабильный JSON (sorted keys, indent 2)."""
    return json.dumps(
        inventory_to_dict(result),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def emit_markdown(result: MapBuildResult) -> str:
    """Опциональный human view; не единственный SoT."""
    lines = [
        "# WB API Master map",
        "",
        f"schema: `{result.schema_version}`",
        f"entries: {len(result.entries)}",
        f"gaps: {len(result.gaps)}",
        "",
        "| family | method | path |",
        "|--------|--------|------|",
    ]
    for entry in result.entries:
        lines.append(f"| {entry.family} | {entry.method} | `{entry.path}` |")
    if result.gaps:
        lines.extend(["", "## Gaps", ""])
        for gap in result.gaps:
            lines.append(f"- `{gap.family}`: {gap.reason}")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """CLI args для offline map build (без shop_id / token)."""
    parser = argparse.ArgumentParser(
        description=(
            "Build API Master inventory map (path × method × family) from "
            "local generated vN swagger YAML. Offline: no network, no codegen."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / ".tmp" / "wb-api-master-map" / "inventory.json",
        help="Path for machine-readable JSON inventory (SoT).",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=None,
        help="Optional human-readable markdown view path.",
    )
    parser.add_argument(
        "--generated-root",
        type=Path,
        default=None,
        help="Override generated/ root (default: app/core/mp/wb/api/generated).",
    )
    parser.add_argument(
        "--family",
        action="append",
        dest="families",
        default=None,
        help="Limit to family key (repeatable). Default: all discovered.",
    )
    parser.add_argument(
        "--force-version",
        type=int,
        default=None,
        help="Use exact vN for all selected families instead of latest.",
    )
    parser.add_argument(
        "--swagger-file",
        type=Path,
        default=None,
        help="Explicit local swagger YAML (requires --family once).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Entrypoint: offline map → JSON (+ optional markdown).

    Exit 0 если есть entries; 1 при полном провале / пустом allowlist.
    Spec: Total source failure is not silent success; no shop access.
    """
    args = parse_args(argv)

    if args.swagger_file is not None:
        families_arg: list[str] = list(args.families or [])
        if len(families_arg) != 1:
            print(
                "error: --swagger-file requires exactly one --family",
                file=sys.stderr,
            )
            return 1
        swagger_file: Path = args.swagger_file
        result = build_map_from_yaml_paths([(families_arg[0], swagger_file)])
    else:
        roots = default_family_roots(args.generated_root)
        if not roots:
            result = MapBuildResult(schema_version=SCHEMA_VERSION)
            result.gaps.append(
                SourceGap(family="*", reason="generated_root_missing_or_empty")
            )
        else:
            result = build_map_from_family_roots(
                roots,
                force_version=args.force_version,
                families=args.families,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(emit_json(result), encoding="utf-8")
    if args.markdown is not None:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(emit_markdown(result), encoding="utf-8")

    print(
        f"wrote {args.output} entries={len(result.entries)} gaps={len(result.gaps)}"
    )
    if not result.ok:
        print(
            "error: no inventory entries produced (honest failure, not silent success)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
