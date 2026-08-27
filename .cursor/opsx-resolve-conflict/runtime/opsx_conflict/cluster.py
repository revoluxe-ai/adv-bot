"""Semantic clustering по evidence — authority per path, не per cluster."""

from __future__ import annotations

import hashlib
from pathlib import Path

from opsx_conflict.models import AuthorityLane, PartitionedPath, SemanticCluster


def _cluster_key(paths: list[str], evidence: list[str]) -> str:
    raw = f"{','.join(sorted(paths))}:{','.join(sorted(evidence))}"
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
        alt = f"tests/{norm[4:].replace('.py', '_test.py')}"
        if alt in all_paths:
            cluster.append(alt)
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
    prefix = (
        norm.split("/", 2)[0] + "/" + norm.split("/", 2)[1]
        if norm.count("/") >= 2
        else norm
    )
    return [
        p
        for p in all_paths
        if p != path and p.replace("\\", "/").startswith(prefix)
    ]


def _collect_relations(
    path: str,
    part: PartitionedPath,
    partitions: list[PartitionedPath],
    all_paths: set[str],
) -> tuple[set[str], list[str]]:
    """Semantic neighbors for ``path``; authority-neutral linking."""

    members = {path}
    evidence: list[str] = []

    prefix = _dir_prefix(path)
    if prefix:
        for other in partitions:
            if other.path not in members and other.lane == part.lane:
                if _dir_prefix(other.path) == prefix:
                    members.add(other.path)
                    evidence.append(f"shared_dir:{prefix}")

    for m in _test_production_pair(path, all_paths):
        if m in all_paths:
            members.add(m)
            evidence.append("test_production_relation")

    for m in _command_runtime_relations(path, all_paths):
        members.add(m)
        evidence.append("command_runtime_relation")

    for m in _spec_relations(path, all_paths):
        members.add(m)
        evidence.append("spec_proximity")

    return members, evidence


def build_clusters(partitions: list[PartitionedPath]) -> list[SemanticCluster]:
    """CLUSTER: semantic units; per-path lane из partition, не из cluster."""

    if not partitions:
        return []

    all_paths = {p.path for p in partitions}
    by_path = {p.path: p for p in partitions}

    # Union-find — transitive semantic membership без lane grouping
    parent: dict[str, str] = {p.path: p.path for p in partitions}
    group_evidence: dict[str, list[str]] = {p.path: [] for p in partitions}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for part in partitions:
        related, evidence = _collect_relations(
            part.path, part, partitions, all_paths
        )
        for ev in evidence:
            if ev not in group_evidence[part.path]:
                group_evidence[part.path].append(ev)
        for other in related:
            if other != part.path:
                union(part.path, other)
                for ev in evidence:
                    root = find(other)
                    if ev not in group_evidence[root]:
                        group_evidence[root].append(ev)

    groups: dict[str, set[str]] = {}
    for part in partitions:
        root = find(part.path)
        groups.setdefault(root, set()).add(part.path)

    clusters: list[SemanticCluster] = []
    for root, member_set in groups.items():
        paths_sorted = sorted(member_set)
        evidence = sorted(set(group_evidence.get(root, [])))
        member_lanes = {p: by_path[p].lane.value for p in paths_sorted}
        lanes_set = {by_path[p].lane for p in paths_sorted}
        homogeneous = len(lanes_set) == 1
        cluster_lane = next(iter(lanes_set)) if homogeneous else None
        cid = _cluster_key(paths_sorted, evidence)
        clusters.append(
            SemanticCluster(
                cluster_id=cid,
                paths=paths_sorted,
                member_lanes=member_lanes,
                authority_homogeneous=homogeneous,
                lane=cluster_lane,
                evidence=evidence,
            )
        )

    return clusters
