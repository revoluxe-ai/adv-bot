"""Кодирование manifest + payloads в ZIP (stdlib)."""

from __future__ import annotations

import io
import zipfile
from typing import Any

from app.modules.ai_package_v1.domain.manifest import (
    MANIFEST_LOGICAL_NAME,
    DomainPayload,
    ExportManifest,
    build_file_descriptors,
    sha256_hex,
)

def encode_package(
    manifest: ExportManifest,
    payloads: list[DomainPayload],
) -> bytes:
    """
    Упаковывает доменный manifest и payload-файлы в ZIP.

    Manifest bytes вычисляются после заполнения ``files`` дескрипторами.
    """
    manifest.files = build_file_descriptors(payloads)
    manifest_bytes = manifest.manifest_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for payload in sorted(payloads, key=lambda p: p.logical_name):
            zf.writestr(payload.logical_name, payload.content)
        zf.writestr(MANIFEST_LOGICAL_NAME, manifest_bytes)
    return buffer.getvalue()


def decode_package(zip_bytes: bytes) -> tuple[dict[str, Any], dict[str, bytes]]:
    """
    Извлекает manifest dict и map logical_name → content из ZIP.

    Raises:
        ValueError: если manifest.json отсутствует или не парсится.
    """
    import json

    with zipfile.ZipFile(io.BytesIO(zip_bytes), mode="r") as zf:
        if MANIFEST_LOGICAL_NAME not in zf.namelist():
            raise ValueError(f"missing {MANIFEST_LOGICAL_NAME}")
        manifest_raw = zf.read(MANIFEST_LOGICAL_NAME)
        manifest: dict[str, Any] = json.loads(manifest_raw.decode("utf-8"))
        files: dict[str, bytes] = {}
        for name in zf.namelist():
            if name == MANIFEST_LOGICAL_NAME:
                continue
            files[name] = zf.read(name)
    return manifest, files


def payload_sha256_map(files: dict[str, bytes]) -> dict[str, str]:
    """Хеши содержимого payload-файлов."""
    return {name: sha256_hex(content) for name, content in sorted(files.items())}
