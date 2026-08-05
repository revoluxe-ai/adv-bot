"""Unit: generator mapping для Reports OpenAPI client (INC-RO-06)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load_generator_module():
    """Загрузить tools/generate_wb_api_client.py как модуль."""
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "generate_wb_api_client.py"
    spec = importlib.util.spec_from_file_location("wb_generator_reports_map", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reports_present_in_swagger_targets() -> None:
    """Requirement: Reports client generation procedure — reports в SWAGGER_TARGETS."""
    mod = _load_generator_module()
    assert "reports" in mod.SWAGGER_TARGETS
    target = mod.SWAGGER_TARGETS["reports"]
    assert target.spec_filename == "12-reports.yaml"
    assert target.skip_transliteration is True
    assert "12-reports.yaml" in target.spec_url
    assert target.spec_url.endswith("/yaml/en/12-reports.yaml")
    assert target.package_name == "reports_client"
    assert str(target.target_root).replace("\\", "/").endswith(
        "app/core/mp/wb/api/generated/reports"
    )
