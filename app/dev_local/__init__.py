"""Локальная разработка: kubectl port-forward к сервисам в Kubernetes."""

from app.dev_local.k8s_tunnels import (
    start_dev_tunnels_monitor,
    wait_for_dev_tunnels_ready,
)

__all__ = ["start_dev_tunnels_monitor", "wait_for_dev_tunnels_ready"]
