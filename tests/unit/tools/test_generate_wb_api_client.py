from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

import pytest

pytestmark = pytest.mark.unit


def _load_generator_module():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "generate_wb_api_client.py"
    spec = importlib.util.spec_from_file_location("wb_generator", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_args(
    *,
    target_root: Path,
    force_version: int | None = None,
    check_spec_changed: bool = False,
    use_cached_spec: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        spec_key="promotion",
        spec_url=None,
        spec_filename=None,
        package_name=None,
        target_root=target_root,
        force_version=force_version,
        meta="none",
        python_cmd="openapi-python-client",
        check_spec_changed=check_spec_changed,
        use_cached_spec=use_cached_spec,
    )


def test_reports_swagger_target_mapping_english_no_transliteration() -> None:
    """INC-RO-06: `reports` в SWAGGER_TARGETS — en 12-reports, skip_transliteration.

    Requirement: Reports client generation procedure / generator mapping.
    """
    mod = _load_generator_module()
    assert "reports" in mod.SWAGGER_TARGETS
    target = mod.SWAGGER_TARGETS["reports"]
    assert target.spec_filename == "12-reports.yaml"
    assert "12-reports.yaml" in target.spec_url
    assert "/en/" in target.spec_url or target.spec_url.endswith("12-reports.yaml")
    assert target.skip_transliteration is True
    assert target.package_name == "reports_client"
    assert target.target_root.name == "reports"


def test_spec_lock_roundtrip_has_expected_fields(tmp_path: Path) -> None:
    mod = _load_generator_module()
    spec_bytes = b"openapi: 3.0.0\ninfo:\n  title: x\n"
    lock_data = mod.build_spec_lock(
        spec_key="promotion",
        spec_url="https://example.test/08-promotion.yaml",
        spec_filename="08-promotion.yaml",
        spec_bytes=spec_bytes,
        generator="openapi-python-client",
        generator_meta="none",
    )
    lock_path = tmp_path / "spec.lock.json"
    mod.write_spec_lock(lock_path, lock_data)
    loaded = mod.read_spec_lock(lock_path)

    assert loaded["spec_key"] == "promotion"
    assert loaded["spec_filename"] == "08-promotion.yaml"
    assert loaded["sha256"] == mod.compute_sha256(spec_bytes)
    assert loaded["size_bytes"] == len(spec_bytes)
    assert loaded["generator"] == "openapi-python-client"
    assert loaded["generator_meta"] == "none"
    assert "downloaded_at_utc" in loaded


def test_main_writes_lock_after_download(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mod = _load_generator_module()
    args = _make_args(target_root=tmp_path)
    monkeypatch.setattr(mod, "parse_args", lambda: args)

    spec_bytes = b"openapi: 3.0.0\ninfo:\n  title: promotion\n"
    monkeypatch.setattr(mod, "fetch_spec_bytes", lambda _url: spec_bytes)

    def _fake_run_generator(_spec_path: Path, output_path: Path, _meta: str, _cmd: str) -> None:
        (output_path / "__init__.py").write_text("", encoding="utf-8")
        (output_path / "client.py").write_text("# generated\n", encoding="utf-8")

    monkeypatch.setattr(mod, "run_generator", _fake_run_generator)

    exit_code = mod.main()
    assert exit_code == 0

    lock_path = tmp_path / "v1" / "swagger" / "spec.lock.json"
    assert lock_path.exists()
    lock_data = mod.read_spec_lock(lock_path)
    assert lock_data["sha256"] == mod.compute_sha256(spec_bytes)
    assert lock_data["size_bytes"] == len(spec_bytes)


def test_check_spec_changed_returns_10_on_hash_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mod = _load_generator_module()
    version_swagger = tmp_path / "v2" / "swagger"
    version_swagger.mkdir(parents=True)
    lock_path = version_swagger / "spec.lock.json"
    mod.write_spec_lock(
        lock_path,
        {
            "spec_key": "promotion",
            "spec_url": "https://example.test/08-promotion.yaml",
            "spec_filename": "08-promotion.yaml",
            "sha256": "abc",
            "size_bytes": 10,
            "downloaded_at_utc": "2026-01-01T00:00:00+00:00",
            "generator": "openapi-python-client",
            "generator_meta": "none",
        },
    )
    args = _make_args(target_root=tmp_path, check_spec_changed=True)
    monkeypatch.setattr(mod, "parse_args", lambda: args)
    monkeypatch.setattr(mod, "fetch_spec_bytes", lambda _url: b"different-bytes")

    assert mod.main() == 10


def test_use_cached_spec_uses_local_file_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mod = _load_generator_module()
    spec_filename = "08-promotion.yaml"
    spec_bytes = b"cached-spec"
    target_dir = tmp_path / "v4"
    swagger_dir = target_dir / "swagger"
    swagger_dir.mkdir(parents=True)
    (target_dir / "__init__.py").write_text("", encoding="utf-8")
    spec_path = swagger_dir / spec_filename
    spec_path.write_bytes(spec_bytes)
    mod.write_spec_lock(
        swagger_dir / "spec.lock.json",
        {
            "spec_key": "promotion",
            "spec_url": "https://example.test/08-promotion.yaml",
            "spec_filename": spec_filename,
            "sha256": mod.compute_sha256(spec_bytes),
            "size_bytes": len(spec_bytes),
            "downloaded_at_utc": "2026-01-01T00:00:00+00:00",
            "generator": "openapi-python-client",
            "generator_meta": "none",
        },
    )

    args = _make_args(target_root=tmp_path, force_version=4, use_cached_spec=True)
    monkeypatch.setattr(mod, "parse_args", lambda: args)

    def _fail_network(_url: str) -> bytes:
        raise AssertionError("network must not be used in cached mode")

    monkeypatch.setattr(mod, "fetch_spec_bytes", _fail_network)

    def _fake_run_generator(_spec_path: Path, output_path: Path, _meta: str, _cmd: str) -> None:
        (output_path / "__init__.py").write_text("", encoding="utf-8")
        (output_path / "client.py").write_text("# generated from cache\n", encoding="utf-8")

    monkeypatch.setattr(mod, "run_generator", _fake_run_generator)

    assert mod.main() == 0

