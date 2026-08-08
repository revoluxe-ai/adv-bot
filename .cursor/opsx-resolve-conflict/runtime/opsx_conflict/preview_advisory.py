"""Windows PREVIEW_ONLY advisory conflict analysis (read-only).

ADR-OPSX-RC-PLATFORM-001 / WINDOWS_PREVIEW_ONLY:

- Explains active merge/rebase conflicts from stage 1/2/3 blobs.
- Never writes worktree/index/refs.
- Missing authority producer / OS_VERIFIED sandbox are LIMITATIONS, not STOP.
- Does not claim authenticated resolution or GO readiness.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .attestation import PACKAGE_VERSION, assert_supported_platform
from .errors import StopRequired
from .preview_readonly_git import PreviewReadonlyGit

PREVIEW_REPORT_SCHEMA = "opsx-resolve-conflict/preview-report/v1"
SAFETY_LABEL_RU = (
    "ADVISORY PREVIEW — изменения не применялись.\n"
    "Решение должен проверить и применить пользователь."
)


@dataclass(frozen=True)
class StageBlob:
    """One unmerged stage blob identity + optional text."""

    stage: int
    mode: str
    oid: str
    text: str | None


@dataclass(frozen=True)
class ConflictPathSnapshot:
    """Unmerged path with stage blobs."""

    path: str
    stages: dict[int, StageBlob]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _parse_unmerged(raw: str) -> list[tuple[str, str, int, str]]:
    """Parse ``git ls-files --unmerged -z`` into (mode, oid, stage, path)."""
    rows: list[tuple[str, str, int, str]] = []
    for rec in raw.split("\0"):
        if not rec.strip():
            continue
        try:
            meta, path = rec.split("\t", 1)
            mode, oid, stage_s = meta.split()
            rows.append((mode, oid, int(stage_s), path.replace("\\", "/")))
        except ValueError as exc:
            raise StopRequired("PREVIEW_UNMERGED_PARSE_FAILED", {"record": rec[:200]}) from exc
    return rows


def _detect_operation(git: PreviewReadonlyGit) -> str:
    """Detect merge vs rebase from read-only Git state."""
    git_dir = git.resolve_git_dir()
    root = Path(git.repo_root)
    gd = Path(git_dir)
    if not gd.is_absolute():
        gd = root / gd
    if (gd / "MERGE_HEAD").is_file():
        return "merge"
    if (gd / "rebase-merge").is_dir() or (gd / "rebase-apply").is_dir():
        return "rebase"
    if (gd / "CHERRY_PICK_HEAD").is_file():
        return "cherry-pick"
    raise StopRequired("PREVIEW_NO_ACTIVE_CONFLICT_OPERATION")


def _capture_state(
    git: PreviewReadonlyGit,
    *,
    paths: list[str],
) -> dict[str, Any]:
    """Capture refs/index/unmerged/worktree digests for immutability checks."""
    git_dir = git.resolve_git_dir()
    gd = Path(git_dir)
    if not gd.is_absolute():
        gd = Path(git.repo_root) / gd
    index_path = gd / "index"
    index_digest = (
        _sha256_bytes(index_path.read_bytes()) if index_path.is_file() else None
    )
    refs = git.read_refs()
    refs_digest = _sha256_text(refs or "")
    unmerged = git.read_unmerged_index()
    unmerged_digest = _sha256_text(unmerged or "")
    worktree: dict[str, str | None] = {}
    for path in paths:
        wp = Path(git.repo_root) / path
        if wp.is_file() and not wp.is_symlink():
            worktree[path] = _sha256_bytes(wp.read_bytes())
        else:
            worktree[path] = None
    head = git.resolve_head()
    return {
        "git_dir": str(gd),
        "index_digest": index_digest,
        "refs_digest": refs_digest,
        "unmerged_digest": unmerged_digest,
        "worktree_digests": worktree,
        "head": head,
        "unmerged_raw": unmerged or "",
    }


def _load_conflict_paths(
    git: PreviewReadonlyGit,
    *,
    path_filter: str | None,
) -> list[ConflictPathSnapshot]:
    """Load stage 1/2/3 blobs for unmerged paths."""
    raw = git.read_unmerged_index()
    rows = _parse_unmerged(raw or "")
    if not rows:
        raise StopRequired("PREVIEW_NO_UNMERGED_PATHS")
    by_path: dict[str, dict[int, StageBlob]] = {}
    for mode, oid, stage, path in rows:
        by_path.setdefault(path, {})[stage] = StageBlob(stage, mode, oid, None)
    paths = sorted(by_path)
    if path_filter:
        norm = path_filter.replace("\\", "/")
        if norm not in by_path:
            raise StopRequired(
                "PREVIEW_PATH_NOT_UNMERGED",
                {"path": norm, "unmerged": paths},
            )
        paths = [norm]
    snapshots: list[ConflictPathSnapshot] = []
    for path in paths:
        stages: dict[int, StageBlob] = {}
        for stage, meta in by_path[path].items():
            blob = git.read_stage_blob(meta.oid)
            # cat-file may return binary; keep text with replace.
            stages[stage] = StageBlob(stage, meta.mode, meta.oid, blob)
        snapshots.append(ConflictPathSnapshot(path=path, stages=stages))
    return snapshots


def _summarize_side(text: str | None, *, label: str) -> str:
    """Concise factual summary of one side's blob."""
    if text is None:
        return f"{label}: blob отсутствует в индексе (unmerged stage missing)."
    lines = text.splitlines()
    funcs = re.findall(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", text, flags=re.M)
    classes = re.findall(r"^\s*class\s+(\w+)\s*[\(:]", text, flags=re.M)
    bits = [f"{label}: {len(lines)} строк(и)."]
    if funcs:
        bits.append("Функции: " + ", ".join(funcs[:12]) + ("…" if len(funcs) > 12 else ""))
    if classes:
        bits.append("Классы: " + ", ".join(classes[:8]))
    return " ".join(bits)


def _diff_lines(a: str | None, b: str | None) -> tuple[list[str], list[str]]:
    """Return lines only in a / only in b (simple set diff of stripped lines)."""
    sa = {ln for ln in (a or "").splitlines() if ln.strip()}
    sb = {ln for ln in (b or "").splitlines() if ln.strip()}
    return sorted(sa - sb), sorted(sb - sa)


def _build_options(
    *,
    path: str,
    base: str | None,
    ours: str | None,
    theirs: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    """Build resolution options, owner decisions, optional recommendation."""
    owner: list[dict[str, Any]] = []
    options: list[dict[str, Any]] = []
    only_ours, only_theirs = _diff_lines(ours, theirs)
    options.append(
        {
            "id": "keep_ours",
            "title": "Оставить сторону OURS (stage 2)",
            "resulting_behavior": "Поведение как на текущей ветке (ours).",
            "retained_changes": "Все строки/символы stage 2.",
            "discarded_changes": "Все уникальные изменения stage 3.",
            "risks": [
                "Потеря функциональности, внесённой в theirs.",
                "Тесты/контракты, рассчитанные на theirs, могут упасть.",
            ],
            "affected_tests_contracts": [
                "Целевые тесты вокруг изменённых функций path=" + path
            ],
        }
    )
    options.append(
        {
            "id": "keep_theirs",
            "title": "Оставить сторону THEIRS (stage 3)",
            "resulting_behavior": "Поведение как на входящей стороне (theirs).",
            "retained_changes": "Все строки/символы stage 3.",
            "discarded_changes": "Все уникальные изменения stage 2.",
            "risks": [
                "Потеря локальных изменений ours.",
                "Регрессии относительно ожиданий текущей ветки.",
            ],
            "affected_tests_contracts": [
                "Целевые тесты вокруг изменённых функций path=" + path
            ],
        }
    )
    recommendation: dict[str, Any] | None = None
    if only_ours and only_theirs:
        owner.append(
            {
                "id": "product_contract_choice",
                "question": (
                    "Какой контракт поведения должен остаться для "
                    f"{path}: модель ours, модель theirs или явная комбинация?"
                ),
                "why_unprovable": (
                    "Обе стороны содержат уникальные изменения; "
                    "репозиторий не доказывает единственный intended contract."
                ),
                "mark": "inference_gap",
            }
        )
        options.append(
            {
                "id": "manual_combine",
                "title": "Явно скомбинировать ours и theirs",
                "resulting_behavior": (
                    "Поведение после ручного объединения выбранных фрагментов."
                ),
                "retained_changes": "Выбранные фрагменты обеих сторон.",
                "discarded_changes": "Отклонённые фрагменты по решению Owner.",
                "risks": [
                    "Ошибочная комбинация может нарушить оба исходных контракта.",
                    "Требует ручной проверки Owner.",
                ],
                "affected_tests_contracts": [
                    "Все тесты, покрывающие пересекающиеся символы"
                ],
            }
        )
        # Evidence supports multiple valid contracts — no recommendation.
        recommendation = None
    elif only_ours and not only_theirs:
        recommendation = {
            "option_id": "keep_ours",
            "rationale": (
                "Наблюдаемые уникальные изменения есть только на стороне ours; "
                "theirs не добавляет отдельных строк относительно ours."
            ),
        }
    elif only_theirs and not only_ours:
        recommendation = {
            "option_id": "keep_theirs",
            "rationale": (
                "Наблюдаемые уникальные изменения есть только на стороне theirs; "
                "ours не добавляет отдельных строк относительно theirs."
            ),
        }
    else:
        if (ours or "") == (theirs or ""):
            recommendation = {
                "option_id": "keep_ours",
                "rationale": "Тексты stage 2 и stage 3 совпадают.",
            }
        else:
            owner.append(
                {
                    "id": "semantic_equivalence_unknown",
                    "question": (
                        f"Эквивалентны ли семантически варианты {path}, "
                        "несмотря на текстовые различия?"
                    ),
                    "why_unprovable": (
                        "Простой line-diff не доказывает семантическую эквивалентность."
                    ),
                    "mark": "inference_gap",
                }
            )
            recommendation = None
    return options, owner, recommendation


def _human_report_ru(report: dict[str, Any]) -> str:
    """Render Russian human-readable advisory report."""
    lines: list[str] = [SAFETY_LABEL_RU, ""]
    cur = report["CURRENT_CONFLICT"]
    lines.append("## Текущий конфликт")
    lines.append(f"Операция: {cur.get('operation')}")
    lines.append(f"Путь: {cur.get('path')}")
    lines.append(
        "Stage blobs: "
        f"base={cur.get('base_available')} "
        f"ours={cur.get('ours_available')} "
        f"theirs={cur.get('theirs_available')}"
    )
    lines.append("")
    lines.append("## Факты")
    for fact in report.get("FACTS") or []:
        lines.append(f"- {fact}")
    lines.append("")
    lines.append("## OURS")
    lines.append(str(report.get("OURS") or ""))
    lines.append("")
    lines.append("## THEIRS")
    lines.append(str(report.get("THEIRS") or ""))
    lines.append("")
    lines.append("## Семантический конфликт")
    lines.append(str(report.get("SEMANTIC_CONFLICT") or ""))
    lines.append("")
    lines.append("## Интерпретации (выводы, не факты)")
    for item in report.get("INTERPRETATIONS") or []:
        lines.append(f"- [{item.get('mark')}] {item.get('text')}")
    lines.append("")
    lines.append("## Решения Owner")
    decisions = report.get("OWNER_DECISIONS_REQUIRED") or []
    if not decisions:
        lines.append("- Нет: по текущим фактам Owner-решение не требуется.")
    else:
        for d in decisions:
            lines.append(f"- {d.get('question')}")
    lines.append("")
    lines.append("## Варианты разрешения")
    for opt in report.get("RESOLUTION_OPTIONS") or []:
        lines.append(f"### {opt.get('id')}: {opt.get('title')}")
        lines.append(str(opt.get("resulting_behavior") or ""))
    lines.append("")
    rec = report.get("RECOMMENDATION")
    lines.append("## Рекомендация")
    if rec is None:
        lines.append(
            "Рекомендация не обоснована: недостаточно доказательств для "
            "единственного контракта. Нужно решение Owner."
        )
    else:
        lines.append(f"Предпочтительный вариант: {rec.get('option_id')}")
        lines.append(str(rec.get("rationale") or ""))
    lines.append("")
    lines.append("## План проверки")
    for step in report.get("VALIDATION_PLAN") or []:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Ограничения")
    for lim in report.get("LIMITATIONS") or []:
        lines.append(f"- {lim}")
    lines.append("")
    mut = report.get("MUTATION_ASSERTION") or {}
    lines.append("## Неизменность состояния")
    lines.append(
        f"worktree={mut.get('worktree_unchanged')} "
        f"index={mut.get('index_unchanged')} "
        f"refs={mut.get('refs_unchanged')}"
    )
    return "\n".join(lines) + "\n"


def run_preview_advisory(
    repo_root: Path,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Run Windows PREVIEW_ONLY advisory analysis; return report dict.

    Raises:
        StopRequired: typed fail-closed conditions (platform, no conflict,
            mutation, allowlist violation, etc.).
    """
    assert_supported_platform()
    repo = Path(repo_root).resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        # Allow bare detection via rev-parse later.
        pass
    git = PreviewReadonlyGit(repo)
    try:
        operation = _detect_operation(git)
        # First pass: discover paths for worktree digest capture.
        probe = git.read_unmerged_index()
        probe_rows = _parse_unmerged(probe or "")
        if not probe_rows:
            raise StopRequired("PREVIEW_NO_UNMERGED_PATHS")
        all_paths = sorted({row[3] for row in probe_rows})
        if path:
            norm = path.replace("\\", "/")
            if norm not in all_paths:
                raise StopRequired(
                    "PREVIEW_PATH_NOT_UNMERGED",
                    {"path": norm, "unmerged": all_paths},
                )
            focus_paths = [norm]
        else:
            focus_paths = all_paths
        before = _capture_state(git, paths=focus_paths)
        snapshots = _load_conflict_paths(git, path_filter=path)
        # Analyze first selected path as primary report focus.
        primary = snapshots[0]
        base_b = primary.stages.get(1)
        ours_b = primary.stages.get(2)
        theirs_b = primary.stages.get(3)
        base_t = base_b.text if base_b else None
        ours_t = ours_b.text if ours_b else None
        theirs_t = theirs_b.text if theirs_b else None
        if ours_t is None and theirs_t is None:
            raise StopRequired(
                "PREVIEW_STAGE_BLOBS_UNREADABLE",
                {"path": primary.path},
            )
        facts = [
            f"Операция Git: {operation}",
            f"Конфликтный путь: {primary.path}",
            f"Stage1(base) oid={base_b.oid if base_b else None}",
            f"Stage2(ours) oid={ours_b.oid if ours_b else None}",
            f"Stage3(theirs) oid={theirs_b.oid if theirs_b else None}",
            f"HEAD={before['head']}",
        ]
        only_ours, only_theirs = _diff_lines(ours_t, theirs_t)
        facts.append(
            f"Уникальных непустых строк только в ours: {len(only_ours)}; "
            f"только в theirs: {len(only_theirs)}"
        )
        semantic = (
            "Текстовое пересечение unmerged index не доказывает само по себе "
            "семантический конфликт. "
        )
        if only_ours and only_theirs:
            semantic += (
                "Наблюдаются уникальные изменения на обеих сторонах — вероятный "
                "семантический/контрактный конфликт, требующий решения Owner."
            )
        elif only_ours or only_theirs:
            semantic += (
                "Уникальные изменения сосредоточены на одной стороне; "
                "текстовый overlap может быть односторонним."
            )
        else:
            semantic += (
                "Line-set diff не выявил уникальных строк; возможны пробелы/"
                "порядок/семантические отличия без простого line-delta."
            )
        interpretations = [
            {
                "mark": "inference",
                "text": (
                    "Различие sibling-кода само по себе не доказывает дефект; "
                    "нужен intended contract от Owner."
                ),
            }
        ]
        options, owner, recommendation = _build_options(
            path=primary.path,
            base=base_t,
            ours=ours_t,
            theirs=theirs_t,
        )
        validation_plan = [
            f"Точечные тесты/проверки для символов в {primary.path}",
            "Прогон смежных unit-тестов модуля после ручного разрешения",
            "При необходимости — статический анализ затронутого контура",
        ]
        limitations = [
            "Результат advisory; требуется проверка человеком.",
            "Изменения не применялись и не должны применяться автоматически.",
            "Внешний authority declaration producer недоступен / не использовался.",
            "OS_VERIFIED sandbox недоступен / не использовался.",
            "Принадлежность source commit к pack/membership не верифицировалась "
            "(R25-PROCESS-001 остаётся открытым).",
            "Trusted-Git execution не заявляется как atomic (R25-MEDIUM-002 открыт).",
            "GO_CAPABILITY=false; SAFE_USAGE_SCOPE=PREVIEW_ONLY.",
        ]
        after = _capture_state(git, paths=focus_paths)
        if before["index_digest"] != after["index_digest"]:
            raise StopRequired(
                "PREVIEW_INDEX_MUTATION",
                {"before": before["index_digest"], "after": after["index_digest"]},
            )
        if before["refs_digest"] != after["refs_digest"]:
            raise StopRequired(
                "PREVIEW_REFS_MUTATION",
                {"before": before["refs_digest"], "after": after["refs_digest"]},
            )
        if before["unmerged_digest"] != after["unmerged_digest"]:
            raise StopRequired(
                "PREVIEW_UNMERGED_MUTATION",
                {
                    "before": before["unmerged_digest"],
                    "after": after["unmerged_digest"],
                },
            )
        if before["worktree_digests"] != after["worktree_digests"]:
            raise StopRequired(
                "PREVIEW_WORKTREE_MUTATION",
                {
                    "before": before["worktree_digests"],
                    "after": after["worktree_digests"],
                },
            )
        git.assert_ledger_has_no_mutations()
        report: dict[str, Any] = {
            "schema": PREVIEW_REPORT_SCHEMA,
            "status": "PREVIEW_READY",
            "package_version": PACKAGE_VERSION,
            "safe_usage_scope": "PREVIEW_ONLY",
            "go_capability": False,
            "decision_id": "ADR-OPSX-RC-PLATFORM-001",
            "disposition": "WINDOWS_PREVIEW_ONLY",
            "CURRENT_CONFLICT": {
                "operation": operation,
                "path": primary.path,
                "all_unmerged_paths": all_paths,
                "stage_blob_identities": {
                    "1": base_b.oid if base_b else None,
                    "2": ours_b.oid if ours_b else None,
                    "3": theirs_b.oid if theirs_b else None,
                },
                "base_available": base_b is not None,
                "ours_available": ours_b is not None,
                "theirs_available": theirs_b is not None,
            },
            "FACTS": facts,
            "OURS": _summarize_side(ours_t, label="OURS"),
            "THEIRS": _summarize_side(theirs_t, label="THEIRS"),
            "SEMANTIC_CONFLICT": semantic,
            "CONTEXT": {
                "paths_analyzed": [s.path for s in snapshots],
                "note": (
                    "Ограниченный контекст: stage blobs + line-set diff; "
                    "полный call-graph не строится."
                ),
            },
            "INTERPRETATIONS": interpretations,
            "OWNER_DECISIONS_REQUIRED": owner,
            "RESOLUTION_OPTIONS": options,
            "RECOMMENDATION": recommendation,
            "VALIDATION_PLAN": validation_plan,
            "LIMITATIONS": limitations,
            "MUTATION_ASSERTION": {
                "worktree_unchanged": True,
                "index_unchanged": True,
                "refs_unchanged": True,
                "unmerged_unchanged": True,
                "no_mutating_git_commands": True,
                "before": {
                    "index_digest": before["index_digest"],
                    "refs_digest": before["refs_digest"],
                    "unmerged_digest": before["unmerged_digest"],
                    "worktree_digests": before["worktree_digests"],
                },
                "after": {
                    "index_digest": after["index_digest"],
                    "refs_digest": after["refs_digest"],
                    "unmerged_digest": after["unmerged_digest"],
                    "worktree_digests": after["worktree_digests"],
                },
            },
            "command_ledger": git.ledger_as_dicts(),
        }
        report["human_report_ru"] = _human_report_ru(report)
        return report
    except StopRequired:
        raise
    except Exception as exc:  # noqa: BLE001 — convert to typed STOP, never fake success
        raise StopRequired(
            "PREVIEW_UNEXPECTED_EXCEPTION",
            {
                "error": type(exc).__name__,
                "detail": str(exc)[:400],
            },
        ) from exc
