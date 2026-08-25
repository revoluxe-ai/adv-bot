"""
OCI digest provenance для CONTROL Job (без exec RELEASE image).

MVP: проверка формата digest и (опционально) fetch OCI index/manifest
из Harbor Registry API. Multi-arch: из index выбирается platform
linux/amd64 → platform manifest digest.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, cast

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DEFAULT_PLATFORM = "linux/amd64"

# OCI / Docker distribution media types we accept for GETs.
_MANIFEST_ACCEPT = (
    "application/vnd.oci.image.index.v1+json,"
    "application/vnd.docker.distribution.manifest.list.v2+json,"
    "application/vnd.oci.image.manifest.v1+json,"
    "application/vnd.docker.distribution.manifest.v2+json"
)


class ProvenanceError(Exception):
    """Ошибка проверки provenance (невалидный digest / registry / platform)."""


@dataclass(frozen=True)
class ProvenanceResult:
    """Результат проверки digest без запуска RELEASE контейнера."""

    mode: str
    platform: str
    platform_manifest_digest: str
    index_digest: str | None
    registry_checked: bool
    detail: str


def normalize_digest(value: str) -> str:
    """Нормализует и валидирует OCI content digest ``sha256:<64hex>``."""
    digest = (value or "").strip().lower()
    if not DIGEST_RE.match(digest):
        raise ProvenanceError(
            f"invalid OCI digest (want sha256:<64 hex>): {value!r}"
        )
    return digest


def _parse_platform(platform: str) -> tuple[str, str]:
    parts = platform.strip().split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ProvenanceError(f"invalid TARGET_PLATFORM: {platform!r}")
    return parts[0], parts[1]


def _platform_matches(entry: dict[str, Any], os_name: str, arch: str) -> bool:
    plat_obj = entry.get("platform")
    if not isinstance(plat_obj, dict):
        return False
    plat = cast(dict[str, Any], plat_obj)
    return str(plat.get("os")) == os_name and str(plat.get("architecture")) == arch


def resolve_platform_digest_from_index(
    index_doc: dict[str, Any],
    *,
    platform: str = DEFAULT_PLATFORM,
) -> str:
    """Из OCI/Docker image index выбирает digest манифеста целевой platform."""
    os_name, arch = _parse_platform(platform)
    manifests_obj = index_doc.get("manifests")
    if not isinstance(manifests_obj, list) or not manifests_obj:
        raise ProvenanceError("index has no manifests[]")
    manifests = cast(list[dict[str, Any]], manifests_obj)
    matches: list[str] = []
    for item in manifests:
        if not _platform_matches(item, os_name, arch):
            continue
        dig = item.get("digest")
        if isinstance(dig, str) and dig.strip():
            matches.append(normalize_digest(dig))
    if not matches:
        raise ProvenanceError(f"no manifest for platform {platform}")
    if len(matches) > 1:
        raise ProvenanceError(
            f"ambiguous platform {platform}: {len(matches)} manifests"
        )
    return matches[0]


def _is_index_media_type(media_type: str) -> bool:
    mt = (media_type or "").lower()
    return "index" in mt or "manifest.list" in mt


def _assert_registry_digest_matches_pin(registry_digest: str, pinned: str) -> None:
    """
    Если registry вернул Docker-Content-Digest — он обязан совпасть с pin.

    Отсутствие валидного digest в ответе допускается (некоторые registry
    не отдают заголовок); невалидный/чужой digest — ошибка provenance.
    """
    raw = (registry_digest or "").strip()
    if not raw:
        return
    if not DIGEST_RE.match(raw.lower()):
        raise ProvenanceError(
            f"registry Docker-Content-Digest is not a valid sha256: {registry_digest!r}"
        )
    if normalize_digest(raw) != pinned:
        raise ProvenanceError(
            f"registry Docker-Content-Digest mismatch: {raw} != {pinned}"
        )


HttpGet = Callable[[str, dict[str, str]], tuple[dict[str, str], bytes]]


def _default_http_get(url: str, headers: dict[str, str]) -> tuple[dict[str, str], bytes]:
    """HTTP GET через urllib; возвращает (response headers lowercased, body)."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_headers = {k.lower(): v for k, v in resp.headers.items()}
            return raw_headers, resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise ProvenanceError(f"registry HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ProvenanceError(f"registry unreachable for {url}: {exc}") from exc


def _basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def fetch_oci_document(
    *,
    registry_host: str,
    repository: str,
    reference: str,
    username: str = "",
    password: str = "",
    http_get: HttpGet | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    GET ``/v2/<repository>/manifests/<reference>``.

    Returns:
        (Docker-Content-Digest or reference, parsed JSON document)
    """
    getter = http_get or _default_http_get
    host = registry_host.strip().rstrip("/")
    repo = repository.strip().strip("/")
    ref = reference.strip()
    if not host or not repo or not ref:
        raise ProvenanceError("registry_host, repository, reference are required")
    url = f"https://{host}/v2/{repo}/manifests/{ref}"
    headers = {"Accept": _MANIFEST_ACCEPT}
    if username:
        headers["Authorization"] = _basic_auth_header(username, password)
    resp_headers, body = getter(url, headers)
    try:
        doc_obj = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"invalid manifest JSON: {exc}") from exc
    if not isinstance(doc_obj, dict):
        raise ProvenanceError("manifest JSON must be an object")
    doc = cast(dict[str, Any], doc_obj)
    digest_hdr = (resp_headers.get("docker-content-digest") or "").strip().lower()
    resolved = normalize_digest(digest_hdr) if digest_hdr else (
        normalize_digest(ref) if DIGEST_RE.match(ref.lower()) else ref
    )
    return resolved, doc


def verify_release_platform_digest(
    *,
    platform_manifest_digest: str,
    platform: str = DEFAULT_PLATFORM,
    mode: str = "digest_pin",
    expected_platform_manifest_digest: str = "",
    index_digest: str = "",
    registry_host: str = "",
    repository: str = "",
    username: str = "",
    password: str = "",
    http_get: HttpGet | None = None,
) -> ProvenanceResult:
    """
    Проверяет pin platform digest без запуска RELEASE.

    Modes:
      - digest_pin: format + equality с EXPECTED_PLATFORM_MANIFEST_DIGEST
      - registry_manifest: fetch index (optional) / manifest из registry
    """
    pinned = normalize_digest(platform_manifest_digest)
    plat = (platform or DEFAULT_PLATFORM).strip() or DEFAULT_PLATFORM
    mode_norm = (mode or "digest_pin").strip().lower()

    if mode_norm == "digest_pin":
        expected = normalize_digest(expected_platform_manifest_digest or pinned)
        if pinned != expected:
            raise ProvenanceError(
                "platform digest pin mismatch: "
                f"RELEASE={pinned} EXPECTED={expected}"
            )
        return ProvenanceResult(
            mode=mode_norm,
            platform=plat,
            platform_manifest_digest=pinned,
            index_digest=normalize_digest(index_digest) if index_digest.strip() else None,
            registry_checked=False,
            detail="digest_pin equality OK (no registry fetch; no RELEASE exec)",
        )

    if mode_norm != "registry_manifest":
        raise ProvenanceError(f"unknown PROVENANCE_MODE: {mode!r}")

    if not registry_host.strip() or not repository.strip():
        raise ProvenanceError(
            "registry_manifest requires REGISTRY_HOST and REGISTRY_REPOSITORY"
        )

    index_pin = index_digest.strip()
    if index_pin:
        index_pin_norm = normalize_digest(index_pin)
        idx_digest, idx_doc = fetch_oci_document(
            registry_host=registry_host,
            repository=repository,
            reference=index_pin_norm,
            username=username,
            password=password,
            http_get=http_get,
        )
        _assert_registry_digest_matches_pin(str(idx_digest), index_pin_norm)
        media = str(idx_doc.get("mediaType") or "")
        if not _is_index_media_type(media) and "manifests" not in idx_doc:
            raise ProvenanceError(
                f"RELEASE_INDEX_DIGEST is not an image index (mediaType={media!r})"
            )
        resolved_platform = resolve_platform_digest_from_index(
            idx_doc, platform=plat
        )
        if resolved_platform != pinned:
            raise ProvenanceError(
                "platform digest from index != pin: "
                f"resolved={resolved_platform} pin={pinned}"
            )
        # Prove platform manifest blob exists (HEAD/GET without container run).
        plat_digest, plat_doc = fetch_oci_document(
            registry_host=registry_host,
            repository=repository,
            reference=pinned,
            username=username,
            password=password,
            http_get=http_get,
        )
        _assert_registry_digest_matches_pin(str(plat_digest), pinned)
        _ = plat_doc  # existence of JSON body is the proof
        return ProvenanceResult(
            mode=mode_norm,
            platform=plat,
            platform_manifest_digest=pinned,
            index_digest=index_pin_norm,
            registry_checked=True,
            detail=(
                "registry index→platform digest match; "
                "platform manifest fetched (no RELEASE exec)"
            ),
        )

    # No index: fetch platform manifest directly by pin.
    plat_digest, _plat_doc = fetch_oci_document(
        registry_host=registry_host,
        repository=repository,
        reference=pinned,
        username=username,
        password=password,
        http_get=http_get,
    )
    _assert_registry_digest_matches_pin(str(plat_digest), pinned)
    return ProvenanceResult(
        mode=mode_norm,
        platform=plat,
        platform_manifest_digest=pinned,
        index_digest=None,
        registry_checked=True,
        detail="registry platform manifest fetched by pin (no RELEASE exec)",
    )