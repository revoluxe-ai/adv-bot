"""Unit: OCI digest provenance без exec RELEASE."""

from __future__ import annotations

import json

import pytest

from app.db.provenance import (
    ProvenanceError,
    normalize_digest,
    resolve_platform_digest_from_index,
    verify_release_platform_digest,
)


def test_normalize_digest_accepts_sha256() -> None:
    dig = "sha256:" + ("a" * 64)
    assert normalize_digest(dig.upper().replace("SHA256", "sha256")) == dig


def test_normalize_digest_rejects_tag() -> None:
    with pytest.raises(ProvenanceError):
        normalize_digest("latest")


def test_resolve_platform_from_index() -> None:
    amd = "sha256:" + ("b" * 64)
    arm = "sha256:" + ("c" * 64)
    index = {
        "manifests": [
            {
                "digest": arm,
                "platform": {"os": "linux", "architecture": "arm64"},
            },
            {
                "digest": amd,
                "platform": {"os": "linux", "architecture": "amd64"},
            },
        ]
    }
    assert resolve_platform_digest_from_index(index) == amd


def test_digest_pin_mode_equality() -> None:
    dig = "sha256:" + ("d" * 64)
    result = verify_release_platform_digest(
        platform_manifest_digest=dig,
        expected_platform_manifest_digest=dig,
        mode="digest_pin",
    )
    assert result.platform_manifest_digest == dig
    assert result.registry_checked is False


def test_registry_manifest_rejects_index_digest_header_mismatch() -> None:
    """Index GET whose Docker-Content-Digest disagrees with RELEASE_INDEX_DIGEST → fail."""
    index_pin = "sha256:" + ("4" * 64)
    wrong_index = "sha256:" + ("5" * 64)
    plat_pin = "sha256:" + ("6" * 64)
    index_doc = {
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "digest": plat_pin,
                "platform": {"os": "linux", "architecture": "amd64"},
            }
        ],
    }

    def fake_get(url: str, headers: dict[str, str]) -> tuple[dict[str, str], bytes]:
        if index_pin in url:
            return (
                {"docker-content-digest": wrong_index},
                json.dumps(index_doc).encode(),
            )
        raise AssertionError(f"unexpected url {url}")

    with pytest.raises(ProvenanceError, match="Docker-Content-Digest mismatch"):
        verify_release_platform_digest(
            platform_manifest_digest=plat_pin,
            index_digest=index_pin,
            mode="registry_manifest",
            registry_host="harbor.example",
            repository="proj/adv-bot",
            username="u",
            password="p",
            http_get=fake_get,
        )


def test_registry_manifest_index_path_rejects_platform_digest_mismatch() -> None:
    """Index→platform pin OK, but registry Content-Digest for platform differs → fail."""
    index_dig = "sha256:" + ("1" * 64)
    plat_pin = "sha256:" + ("2" * 64)
    wrong_plat = "sha256:" + ("3" * 64)
    index_doc = {
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "digest": plat_pin,
                "platform": {"os": "linux", "architecture": "amd64"},
            }
        ],
    }
    plat_doc = {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "layers": [],
    }

    def fake_get(url: str, headers: dict[str, str]) -> tuple[dict[str, str], bytes]:
        if index_dig in url:
            return (
                {"docker-content-digest": index_dig},
                json.dumps(index_doc).encode(),
            )
        if plat_pin in url:
            return (
                {"docker-content-digest": wrong_plat},
                json.dumps(plat_doc).encode(),
            )
        raise AssertionError(f"unexpected url {url}")

    with pytest.raises(ProvenanceError, match="Docker-Content-Digest mismatch"):
        verify_release_platform_digest(
            platform_manifest_digest=plat_pin,
            index_digest=index_dig,
            mode="registry_manifest",
            registry_host="harbor.example",
            repository="proj/adv-bot",
            username="u",
            password="p",
            http_get=fake_get,
        )


def test_registry_manifest_resolves_index(monkeypatch: pytest.MonkeyPatch) -> None:
    index_dig = "sha256:" + ("e" * 64)
    plat_dig = "sha256:" + ("f" * 64)
    index_doc = {
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "digest": plat_dig,
                "platform": {"os": "linux", "architecture": "amd64"},
            }
        ],
    }
    plat_doc = {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "layers": [],
    }

    def fake_get(url: str, headers: dict[str, str]) -> tuple[dict[str, str], bytes]:
        assert "Authorization" in headers
        if index_dig in url:
            return (
                {"docker-content-digest": index_dig},
                json.dumps(index_doc).encode(),
            )
        if plat_dig in url:
            return (
                {"docker-content-digest": plat_dig},
                json.dumps(plat_doc).encode(),
            )
        raise AssertionError(f"unexpected url {url}")

    result = verify_release_platform_digest(
        platform_manifest_digest=plat_dig,
        index_digest=index_dig,
        mode="registry_manifest",
        registry_host="harbor.example",
        repository="proj/adv-bot",
        username="u",
        password="p",
        http_get=fake_get,
    )
    assert result.registry_checked is True
    assert result.platform_manifest_digest == plat_dig
