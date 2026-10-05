"""Доменный manifest AI Package v1 (независим от ZIP-транспорта)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.modules.ai_package_v1.domain.dataset_card import DatasetCard
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.serialization import canonical_json_bytes

PACKAGE_SCHEMA_VERSION = "1.0.0"
MANIFEST_LOGICAL_NAME = "manifest.json"


class PayloadFileDescriptor(BaseModel):
    """Описание файла payload в manifest с хешем содержимого."""

    logical_name: str
    dataset_id: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class DomainPayload:
    """Именованный payload до упаковки в ZIP."""

    logical_name: str
    dataset_id: str
    content: bytes


def sha256_hex(content: bytes) -> str:
    """SHA-256 содержимого файла (hex, lowercase)."""
    return hashlib.sha256(content).hexdigest()


def build_file_descriptors(payloads: list[DomainPayload]) -> list[PayloadFileDescriptor]:
    """Строит descriptors в стабильном порядке по logical_name."""
    ordered = sorted(payloads, key=lambda p: p.logical_name)
    return [
        PayloadFileDescriptor(
            logical_name=p.logical_name,
            dataset_id=p.dataset_id,
            sha256=sha256_hex(p.content),
            size_bytes=len(p.content),
        )
        for p in ordered
    ]


class ExportManifest(BaseModel):
    """Версионированный manifest пакета."""

    package_schema_version: str = Field(default=PACKAGE_SCHEMA_VERSION)
    shop_id: int
    period: ExportPeriod
    generated_at: str
    datasets: list[DatasetCard]
    files: list[PayloadFileDescriptor] = Field(default_factory=list)

    def validate_cards(self) -> None:
        """Проверяет семантику всех карточек."""
        for card in self.datasets:
            card.validate_semantics()

    def to_domain_dict(self) -> dict[str, Any]:
        """Словарь manifest для канонической сериализации."""
        self.validate_cards()
        ordered_cards = sorted(self.datasets, key=lambda c: str(c.dataset_id))
        ordered_files = sorted(self.files, key=lambda f: f.logical_name)
        return {
            "package_schema_version": self.package_schema_version,
            "shop_id": self.shop_id,
            "period": self.period.to_manifest_dict(),
            "generated_at": self.generated_at,
            "datasets": [c.to_manifest_dict() for c in ordered_cards],
            "files": [f.model_dump() for f in ordered_files],
        }

    def manifest_bytes(self) -> bytes:
        """Канонические UTF-8 bytes manifest (детерминированная сериализация)."""
        return canonical_json_bytes(self.to_domain_dict())

    def manifest_sha256(self) -> str:
        """Хеш канонического manifest.json."""
        return sha256_hex(self.manifest_bytes())
