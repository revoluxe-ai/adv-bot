"""Kernel: classify, validate, digest, planner, pipeline."""

from __future__ import annotations

from typing import Any

__all__ = ["dry_run"]


def __getattr__(name: str) -> Any:
    if name == "dry_run":
        from app.modules.wb_sky_control_plane.kernel.pipeline import dry_run

        return dry_run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
