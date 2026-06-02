"""Локальная разработка: опциональный kubectl port-forward (DEV_TUNNELS_ENABLED=true)."""

from app.dev_local.k8s_tunnels import (
    start_dev_tunnels_monitor,
    wait_for_dev_tunnels_ready,
)

__all__ = ["start_dev_tunnels_monitor", "wait_for_dev_tunnels_ready"]
