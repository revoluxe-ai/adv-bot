"""Доменный контракт AI Package v1: manifest, карточки датасетов, семантика coverage."""

from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FreshnessStatus,
    PrimarySource,
    ReasonCode,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import (
    PACKAGE_SCHEMA_VERSION,
    ExportManifest,
    PayloadFileDescriptor,
)

__all__ = [
    "PACKAGE_SCHEMA_VERSION",
    "CollectionOutcome",
    "Coverage",
    "DatasetId",
    "ExportManifest",
    "ExportPeriod",
    "FreshnessStatus",
    "PayloadFileDescriptor",
    "PrimarySource",
    "ReasonCode",
]
