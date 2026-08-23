"""Semantic clustering по evidence, не по именам."""

from __future__ import annotations

import hashlib
from pathlib import Path

from opsx_conflict.models import AuthorityLane, PartitionedPath, SemanticCluster


def _cluster_key(lane: AuthorityLane, paths: list[str]) -> str:
    raw = f"{lane.value}:{','.join(sorted(paths))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _dir_prefix(path: str) -> str:
    if "/" in path:
        return path.rsplit("/", 1)[0]
    return ""


def _test_production_pair(path: str, all_paths: set[str]) -> list[str]:
    """Evidence: tests/** ↔ app/** pairing."""

    norm = path.replace("\\", "/")
    cluster: list[str] = [path]
    if norm.startswith("tests/") and norm.endswith(".py"):
        # tests/unit/app/foo_test.py → app/foo.py heuristic
        rest = norm[6:]
        if rest.startswith("unit/"):
            rest = rest[5:]
        prod = f"app/{rest.replace('_test.py', '.py').replace('test_', '')}"
        if prod in all_paths:
            cluster.append(prod)
    elif norm.startswith("app/") and norm.endswith(".py"):
        test_guess = f"tests/unit/{norm[4:].replace('.py', '_test.py')}"
        if test_guess in all_paths:
            cluster.append(test_guess)
    return cluster


def _command_runtime_relations(path: str, all_paths: set[str]) -> list[str]:
    """Evidence: command ↔ packaged runtime companions."""

    norm = path.replace("\\", "/")
    related: list[str] = []
    if norm.startswith(".cursor/commands/") and norm.endswith(".md"):
        stem = Path(norm).stem
        for other in all_paths:
            on = other.replace("\\", "/")
            if "opsx-resolve-conflict" in on or stem.replace("opsx-", "") in on:
                related.append(other)
    if norm.startswith(".cursor/opsx-resolve-conflict/"):
        for other in all_paths:
            on = other.replace("\\", "/")
            if on.startswith(".cursor/commands/") and "resolve-conflict" in on:
                related.append(other)
    return related


def _spec_relations(path: str, all_paths: set[str]) -> list[str]:
    norm = path.replace("\\", "/")
    if not norm.startswith("openspec/"):
        return []
    prefix = norm.split("/", 2)[0] + "/" + norm.split("/", 2)[1] if norm.count("/") >= 2 else norm
    return [
        p for p in all_paths
        if p != path and p.replace("\\", "/").startswith(prefix)
    ]


def build_clusters(partitions: list[PartitionedPath]) -> list[SemanticCluster]:
    """CLUSTER: связанные paths в bounded semantic units."""

    all_paths = {p.path for p in partitions}
    by_lane: dict[AuthorityLane, list[PartitionedPath]] = {}
    for p in partitions:
        by_lane.setdefault(p.lane, []).append(p)

    clusters: list[SemanticCluster] = []
    for lane, lane_paths in by_lane.items():
        assigned: set[str] = set()
        for part in lane_paths:
            if part.path in assigned:
                continue
            members = {part.path}
            evidence: list[str] = [f"lane:{lane.value}"]

            prefix = _dir_prefix(part.path)
            if prefix:
                for other in lane_paths:
                    if other.path not in members and _dir_prefix(other.path) == prefix:
                        members.add(other.path)
                        evidence.append(f"shared_dir:{prefix}")

            pair = _test_production_pair(part.path, all_paths)
            for m in pair:
                if m in all_paths:
                    members.add(m)
                    evidence.append("test_production_relation")

            for m in _command_runtime_relations(part.path, all_paths):
                members.add(m)
                evidence.append("command_runtime_relation")

            for m in _spec_relations(part.path, all_paths):
                members.add(m)
                evidence.append("spec_proximity")

            paths_sorted = sorted(members)
            cid = _cluster_key(lane, paths_sorted)
            clusters.append(
                SemanticCluster(
                    cluster_id=cid,
                    lane=lane,
                    paths=paths_sorted,
                    evidence=evidence,
                )
            )
            assigned.update(members)

    return clusters
