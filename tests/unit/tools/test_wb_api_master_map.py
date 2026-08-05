"""
Unit-тесты offline API Master map (capability wb-api-master-map / INC-RO-03).

Проверяют: только объявленные path×method, family от источника, детерминизм,
честные gaps, отсутствие shop_id/WB, inventory не-GET methods.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_YAML = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "wb_api_master_map"
    / "minimal_openapi.yml"
)
MODULE_PATH = REPO_ROOT / "tools" / "wb_api_master_map.py"


def _load_map_module():
    """Загрузить tools/wb_api_master_map.py как модуль (как generate_wb_api_client tests)."""
    spec = importlib.util.spec_from_file_location("wb_api_master_map", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # Ensure sibling tools/ is importable for optional SWAGGER_TARGETS
    tools_dir = str(MODULE_PATH.parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def map_mod():
    """Production module offline map builder."""
    return _load_map_module()


@pytest.fixture
def fixture_doc() -> dict:
    """Загруженный minimal OpenAPI mapping из fixture YAML."""
    return yaml.safe_load(FIXTURE_YAML.read_text(encoding="utf-8"))


def test_fixture_yaml_exists() -> None:
    """
    Task 1.1: unit-фикстура минимального OpenAPI YAML доступна.

    Spec: wb-api-master-map — основа для offline parse tests.
    """
    assert FIXTURE_YAML.is_file()
    doc = yaml.safe_load(FIXTURE_YAML.read_text(encoding="utf-8"))
    assert "paths" in doc
    assert "/api/v1/items" in doc["paths"]


def test_parse_only_declared_paths_no_invent(map_mod, fixture_doc: dict) -> None:
    """
    Task 1.2: из YAML только объявленные path×method; invent URL нет.

    Spec: Offline API Master map / No invent URL.
    """
    entries = map_mod.parse_openapi_paths(fixture_doc, family="alpha")
    pairs = {(e.path, e.method) for e in entries}
    assert pairs == {
        ("/api/v1/items", "GET"),
        ("/api/v1/items", "POST"),
        ("/api/v1/items/{id}", "GET"),
        ("/api/v1/items/{id}", "DELETE"),
    }
    assert all(not e.path.startswith("https://") for e in entries)
    assert "/invented/path" not in {e.path for e in entries}


def test_family_bound_to_source(map_mod, fixture_doc: dict) -> None:
    """
    Task 1.3: family записи = identity источника fixture.

    Spec: Family bound to swagger source.
    """
    entries = map_mod.parse_openapi_paths(fixture_doc, family="reports")
    assert entries
    assert all(e.family == "reports" for e in entries)


def test_deterministic_inventory_json(map_mod, tmp_path: Path) -> None:
    """
    Task 1.4: два прогона → одинаковый machine-readable JSON.

    Spec: Deterministic inventory artifact.
    """
    sources = [("alpha", FIXTURE_YAML)]
    r1 = map_mod.build_map_from_yaml_paths(sources)
    r2 = map_mod.build_map_from_yaml_paths(sources)
    assert map_mod.emit_json(r1) == map_mod.emit_json(r2)
    payload = json.loads(map_mod.emit_json(r1))
    assert "generated_at" not in payload
    families = [e["family"] for e in payload["entries"]]
    paths = [e["path"] for e in payload["entries"]]
    methods = [e["method"] for e in payload["entries"]]
    assert families == sorted(families)
    # entries sorted by (family, path, method) via MapEntry order
    assert list(zip(families, paths, methods)) == sorted(
        zip(families, paths, methods)
    )


def test_missing_source_honest_gap_no_fabricated(map_mod, tmp_path: Path) -> None:
    """
    Task 1.5: missing/unreadable → gap; полный провал ≠ silent success.

    Spec: Honest gaps without fabricated entries.
    """
    missing = tmp_path / "nope.yaml"
    result = map_mod.build_map_from_yaml_paths([("ghost", missing)])
    assert result.entries == []
    assert result.gaps
    assert result.ok is False
    assert all(g.family == "ghost" for g in result.gaps)

    bad = tmp_path / "bad.yaml"
    bad.write_text("not: [valid: openapi\n", encoding="utf-8")
    bad_result = map_mod.build_map_from_yaml_paths([("broken", bad)])
    assert bad_result.entries == []
    assert bad_result.ok is False
    assert bad_result.gaps


def test_cli_no_shop_id_no_wb_args(map_mod) -> None:
    """
    Task 1.6: CLI не требует shop_id/token; build без WB.

    Spec: Map does not authorize WB calls / Offline build needs no shop access.
    """
    ns = map_mod.parse_args(["--output", str(Path("out.json"))])
    assert "shop_id" not in vars(ns)
    assert "token" not in vars(ns)
    result = map_mod.build_map_from_yaml_paths([("alpha", FIXTURE_YAML)])
    assert result.ok


def test_non_get_methods_inventoried(map_mod, fixture_doc: dict) -> None:
    """
    Task 1.7: не-GET methods из YAML в inventory.

    Spec: Mutation filter out of scope / Declared methods are inventoried.
    """
    entries = map_mod.parse_openapi_paths(fixture_doc, family="alpha")
    methods = {e.method for e in entries}
    assert "POST" in methods
    assert "DELETE" in methods
    assert "GET" in methods


def test_build_from_generated_tree_layout(map_mod, tmp_path: Path) -> None:
    """
    Скан family root vN/swagger/*.yaml → entries + gaps для пустого family.

    Spec: Offline API Master map from local swagger.
    """
    family_root = tmp_path / "generated" / "alpha"
    swagger = family_root / "v2" / "swagger"
    swagger.mkdir(parents=True)
    target = swagger / "minimal.yaml"
    target.write_text(FIXTURE_YAML.read_text(encoding="utf-8"), encoding="utf-8")
    # older version also present — latest with yaml should win
    old = family_root / "v1" / "swagger"
    old.mkdir(parents=True)
    (old / "old.yaml").write_text(
        "openapi: 3.0.0\ninfo: {title: old, version: '1'}\npaths: {}\n",
        encoding="utf-8",
    )

    roots = {"alpha": family_root, "missing": tmp_path / "generated" / "missing"}
    result = map_mod.build_map_from_family_roots(roots)
    assert result.ok
    assert any(s.family == "alpha" and s.version == 2 for s in result.sources)
    assert any(e.family == "alpha" for e in result.entries)
    assert any(g.family == "missing" for g in result.gaps)


def test_main_exit_codes(map_mod, tmp_path: Path) -> None:
    """
    main: success с entries → 0; пустые источники → 1 (не silent success).
    """
    out = tmp_path / "inventory.json"
    code_ok = map_mod.main(
        [
            "--swagger-file",
            str(FIXTURE_YAML),
            "--family",
            "alpha",
            "--output",
            str(out),
            "--markdown",
            str(tmp_path / "view.md"),
        ]
    )
    assert code_ok == 0
    assert out.is_file()
    assert (tmp_path / "view.md").is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["entries"]

    code_fail = map_mod.main(
        [
            "--swagger-file",
            str(tmp_path / "absent.yaml"),
            "--family",
            "ghost",
            "--output",
            str(tmp_path / "empty.json"),
        ]
    )
    assert code_fail == 1
