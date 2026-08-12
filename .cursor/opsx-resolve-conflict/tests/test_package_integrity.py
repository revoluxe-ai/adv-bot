from __future__ import annotations

import json
from pathlib import Path

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]


def test_manifest_and_front_matter_versions_match() -> None:
    manifest_path = PACKAGE_ROOT / "MANIFEST.json"
    command_path = REPO_ROOT / ".cursor/commands/opsx-resolve-conflict.md"
    bundled = PACKAGE_ROOT / "candidate/.cursor/commands/opsx-resolve-conflict.md"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert bundled.is_file(), "bundled command entrypoint missing from package"
    assert (PACKAGE_ROOT / "TRUST_ANCHOR.json").is_file()
    for command_path in (command_path, bundled):
        text = command_path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        _, front, _ = text.split("---", 2)
        metadata = yaml.safe_load(front)
        assert metadata["package_version"] == manifest["package_version"] == "0.39.0"
        assert (
            metadata["contract_schema_version"]
            == manifest["contract_schema_version"]
            == "opsx-resolve-conflict/v2"
        )
    # Typed descriptors may exist only in the working tree; R24 forbids pinning
    # paths absent from origin_source_commit without signed provenance.
    categories = manifest["input_categories"]
    assert set(manifest["required_repo_paths"]) == set(
        categories["package_owned_required"]
    ) | set(categories["host_frozen_contracts"])
    assert set(manifest["host_contract_sha256"]) == set(
        categories["host_frozen_contracts"]
    )
    origin = str(
        manifest.get("origin_source_commit") or manifest.get("source_commit") or ""
    )
    # Clean-unpack runs outside a git checkout; origin binding is ship-time only.
    if origin and (REPO_ROOT / ".git").exists():
        import subprocess

        for rel in categories["host_frozen_contracts"]:
            proc = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{origin}:{rel}"],
                capture_output=True,
                check=False,
            )
            assert proc.returncode == 0, f"host_frozen not in origin: {rel}"
    assert manifest.get("author") == "Cursor"
    assert manifest.get("package_digest")
    assert manifest.get("trust_anchor_sha256")


def test_all_entrypoints_and_schemas_exist() -> None:
    manifest = json.loads(
        (PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8")
    )
    package_root = PACKAGE_ROOT
    for key, rel in manifest["entrypoints"].items():
        if key == "bundled_command":
            assert (package_root / rel).is_file(), rel
        else:
            assert (REPO_ROOT / rel).is_file(), rel
    schemas = list((package_root / "schemas").glob("*.schema.json"))
    assert len(schemas) >= 5
    assert (
        package_root / "schemas" / "authority-declaration.schema.json"
    ).is_file()


def test_review_control_documents_present() -> None:
    for name in (
        "00_SCOPE.md",
        "01_REVIEW_STANDARD.md",
        "02_REQUIRED_CONTEXT.md",
        "03_VERDICT_SCHEMA.md",
        "CHANGELOG.md",
        "AUTHORSHIP.md",
        "REVIEW_REQUEST.md",
        "04_REVISION_CLOSURE_MATRIX.md",
        "CLEAN_UNPACK_TEST_REPORT.json",
        "TRUST_ANCHOR.json",
        "context/OPSX_CONTEXT_EXTRACT.md",
    ):
        assert (PACKAGE_ROOT / name).is_file(), name


def test_all_version_bearing_review_documents_are_r11() -> None:
    """Reject stale review-control lineage in R24 review headers."""
    expected = {
        "AUTHORSHIP.md": ("OPSX_RESOLVE_CONFLICT_COMMAND_001_R39", "0.39.0"),
        "00_SCOPE.md": ("R39", "0.39.0"),
        "01_REVIEW_STANDARD.md": ("R39",),
        "02_REQUIRED_CONTEXT.md": ("R39",),
        "03_VERDICT_SCHEMA.md": ("R39", '"PACKAGE_VERSION": "0.39.0"'),
        "README_REVIEW.md": ("0.39.0",),
        "context/OPSX_CONTEXT_EXTRACT.md": ("R39", "0.39.0"),
    }
    for rel, tokens in expected.items():
        text = (PACKAGE_ROOT / rel).read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, f"{rel} missing {token}"
