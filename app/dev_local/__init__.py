"""LEGACY re-export: kubectl port-forward (очередь на выпиливание с k8s_tunnels).

Канон локали — IP/NodePort из ``.env``, не этот пакет. См. module docstring
``app.dev_local.k8s_tunnels`` и ``DOTO/WORKLOG.md``.
"""

from app.dev_local.k8s_tunnels import (
    start_dev_tunnels_monitor,
    wait_for_dev_tunnels_ready,
)

__all__ = ["start_dev_tunnels_monitor", "wait_for_dev_tunnels_ready"]
