"""Ошибки и предупреждения control plane A1."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ControlPlaneError(BaseModel):
    """Blocking error: one invalid operation rejects the whole ChangeSet."""

    code: str
    message: str
    resource_id: str | None = None
    operation_index: int | None = None
    details: dict[str, str] = Field(default_factory=dict)


class ControlPlaneWarning(BaseModel):
    """Non-blocking diagnostic."""

    code: str
    message: str
    resource_id: str | None = None
    details: dict[str, str] = Field(default_factory=dict)
