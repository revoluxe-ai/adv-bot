"""Non-authoritative binding hints from client."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ApplyBindingHintsV1(BaseModel):
    """Опциональные подсказки digest; сервер пересчитывает и сравнивает."""

    model_config = _FROZEN

    semantic_digest: str | None = None
    preview_digest: str | None = None
