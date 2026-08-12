"""Windows PREVIEW_ONLY advisory conflict analysis (read-only, R40).

Two layers:
1. Evidence — stage blobs + bounded repository context (``preview_context``).
2. Advisory reasoning — fact/inference separation and options; never mutates.

R40 invariant: one PREVIEW invocation analyzes exactly one conflicted path.
When ``--path`` is omitted and multiple unmerged paths exist, STOP with
``PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS`` (no multi-path semantic coverage).

ADR-OPSX-RC-PLATFORM-001 / WINDOWS_PREVIEW_ONLY. GO_CAPABILITY=false.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .attestation import PACKAGE_VERSION, assert_supported_platform
from .errors import StopRequired
from .preview_context import collect_conflict_context
from .preview_readonly_git import PreviewReadonlyGit

PREVIEW_REPORT_SCHEMA = "opsx-resolve-conflict/preview-report/v2"
SAFETY_LABEL_RU = (
    "ADVISORY PREVIEW — изменения не применялись.\n"
    "Решение должен проверить и применить пользователь."
)

_STRONG_AUTHORITY = frozenset(
    {
        "ACCEPTED_DECISION",
        "CURRENT_SPEC",
        "CONTRACT",
        "API_INVARIANT",
    }
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
    path_filter: str,
) -> list[ConflictPathSnapshot]:
    """Load stage 1/2/3 blobs for exactly one unmerged path.

    Args:
        git: Read-only preview Git boundary.
        path_filter: Repository-relative unmerged path to load (required).

    Returns:
        Single-element list of ``ConflictPathSnapshot`` for ``path_filter``.

    Raises:
        StopRequired: No unmerged paths, or ``path_filter`` is not unmerged.
    """
    raw = git.read_unmerged_index()
    rows = _parse_unmerged(raw or "")
    if not rows:
        raise StopRequired("PREVIEW_NO_UNMERGED_PATHS")
    by_path: dict[str, dict[int, StageBlob]] = {}
    for mode, oid, stage, path in rows:
        by_path.setdefault(path, {})[stage] = StageBlob(stage, mode, oid, None)
    inventory = sorted(by_path)
    norm = path_filter.replace("\\", "/")
    if norm not in by_path:
        raise StopRequired(
            "PREVIEW_PATH_NOT_UNMERGED",
            {"path": norm, "unmerged": inventory},
        )
    stages: dict[int, StageBlob] = {}
    for stage, meta in by_path[norm].items():
        blob = git.read_stage_blob(meta.oid)
        stages[stage] = StageBlob(stage, meta.mode, meta.oid, blob)
    return [ConflictPathSnapshot(path=norm, stages=stages)]


def _select_preview_path(
    all_paths: list[str],
    *,
    path: str | None,
) -> str:
    """Resolve the single path this PREVIEW invocation may analyze.

    Args:
        all_paths: Sorted repository-relative unmerged paths.
        path: Optional ``--path`` argument.

    Returns:
        Exactly one selected conflicted path.

    Raises:
        StopRequired: Zero paths, multiple paths without ``--path``, or
            ``--path`` not in the unmerged inventory.
    """
    if not all_paths:
        raise StopRequired("PREVIEW_NO_UNMERGED_PATHS")
    if path:
        norm = path.replace("\\", "/")
        if norm not in all_paths:
            raise StopRequired(
                "PREVIEW_PATH_NOT_UNMERGED",
                {"path": norm, "unmerged": all_paths},
            )
        return norm
    if len(all_paths) > 1:
        raise StopRequired(
            "PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS",
            {
                "unmerged_paths": all_paths,
                "path_count": len(all_paths),
                "hint": (
                    "Pass --path <one-of-unmerged-paths> to analyze a "
                    "single conflict. Multi-path semantic analysis is "
                    "out of scope."
                ),
            },
        )
    return all_paths[0]


def _side_behavior(text: str | None, *, label: str) -> dict[str, Any]:
    """Describe observable behavior of one side without recommending it."""
    if text is None:
        return {
            "label": label,
            "summary_ru": f"{label}: blob отсутствует в индексе.",
            "read_only": None,
            "functions": [],
            "evidence_refs": [],
        }
    funcs = re.findall(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", text, flags=re.M)
    classes = re.findall(r"^\s*class\s+(\w+)\s*[\(:]", text, flags=re.M)
    read_only_vals = re.findall(r"\bread_only\s*=\s*(True|False)\b", text)
    bits = [f"{len(text.splitlines())} строк(и)"]
    if funcs:
        bits.append("функции: " + ", ".join(funcs[:12]))
    if classes:
        bits.append("классы: " + ", ".join(classes[:8]))
    if read_only_vals:
        bits.append("read_only=" + ", ".join(read_only_vals))
    return {
        "label": label,
        "summary_ru": f"{label}: " + "; ".join(bits) + ".",
        "read_only": read_only_vals[-1] if read_only_vals else None,
        "functions": funcs[:12],
        "classes": classes[:8],
        "evidence_refs": [],
    }


def _diff_lines(a: str | None, b: str | None) -> tuple[list[str], list[str]]:
    """Return lines only in a / only in b (observational; never drives recommendation)."""
    sa = {ln for ln in (a or "").splitlines() if ln.strip()}
    sb = {ln for ln in (b or "").splitlines() if ln.strip()}
    return sorted(sa - sb), sorted(sb - sa)


def _strong_evidence(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Return verified strong-authority evidence only (R36 gate)."""
    return [
        e
        for e in (context.get("evidence") or [])
        if e.get("authority_class") in _STRONG_AUTHORITY
        and e.get("authority_verified") is True
    ]


def _recommendation_polarity(excerpt: str) -> str | None:
    """Map verified authority excerpt to a coarse behavioral polarity."""
    low = excerpt.lower()
    existing = any(
        tok in low
        for tok in (
            "existing-users-only",
            "existing_users_only",
            "existing users only",
            "только для существующих",
            "navigation for existing",
        )
    )
    alias = any(
        tok in low
        for tok in (
            "full /start alias",
            "full start alias",
            "алиас /start",
            "create path",
        )
    )
    if existing and not alias:
        return "existing_users_only"
    if alias and not existing:
        return "full_alias"
    return None


def _build_advisory_reasoning(
    *,
    path: str,
    ours_t: str | None,
    theirs_t: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic advisory contract over the evidence packet (no mutation)."""
    ours = _side_behavior(ours_t, label="OURS")
    theirs = _side_behavior(theirs_t, label="THEIRS")
    only_ours, only_theirs = _diff_lines(ours_t, theirs_t)
    evidence = list(context.get("evidence") or [])
    strong = _strong_evidence(context)
    siblings = [e for e in evidence if e.get("authority_class") == "SIBLING_IMPLEMENTATION"]
    tests = [e for e in evidence if e.get("authority_class") == "TEST_EVIDENCE"]
    char_tests = [e for e in tests if e.get("test_kind") == "characterization"]
    contract_tests = [e for e in tests if e.get("test_kind") == "contract"]

    facts: list[dict[str, Any]] = []
    facts.append(
        {
            "text": f"Конфликтный путь: {path}.",
            "evidence_refs": ["conflict_blobs"],
        }
    )
    if ours["read_only"] is not None or theirs["read_only"] is not None:
        facts.append(
            {
                "text": (
                    f"OURS read_only={ours['read_only']}; "
                    f"THEIRS read_only={theirs['read_only']}."
                ),
                "evidence_refs": ["conflict_blobs"],
            }
        )
    if siblings:
        facts.append(
            {
                "text": (
                    "Найдена sibling-реализация: "
                    + ", ".join(sorted({e['path'] for e in siblings})[:5])
                    + "."
                ),
                "evidence_refs": [e["evidence_id"] for e in siblings[:5]],
            }
        )
        # Sibling API difference is a fact when observable in excerpts.
        sib_ro = []
        for e in siblings:
            m = re.search(r"\bread_only\s*=\s*(True|False)\b", e.get("excerpt") or "")
            if m:
                sib_ro.append((e["evidence_id"], m.group(1)))
        if sib_ro and (ours["read_only"] or theirs["read_only"]):
            facts.append(
                {
                    "text": (
                        "Sibling использует read_only="
                        + ", ".join(v for _, v in sib_ro[:3])
                        + " — это наблюдение, не норма."
                    ),
                    "evidence_refs": [i for i, _ in sib_ro[:3]],
                }
            )
    if tests:
        facts.append(
            {
                "text": f"Найдены тестовые упоминания ({len(tests)}).",
                "evidence_refs": [e["evidence_id"] for e in tests[:5]],
            }
        )
    if char_tests:
        facts.append(
            {
                "text": (
                    "Есть characterization-тесты текущего поведения; "
                    "они не доказывают intended product contract."
                ),
                "evidence_refs": [e["evidence_id"] for e in char_tests[:5]],
            }
        )
    if strong:
        facts.append(
            {
                "text": (
                    "Найден verified strong authority: "
                    + ", ".join(
                        sorted(
                            {
                                f"{e['authority_class']}:{e['path']}"
                                f"({e.get('authority_basis')})"
                                for e in strong
                            }
                        )[:5]
                    )
                    + "."
                ),
                "evidence_refs": [e["evidence_id"] for e in strong[:5]],
            }
        )
    unverified_labeled = [
        e
        for e in evidence
        if e.get("authority_class") in _STRONG_AUTHORITY
        and e.get("authority_verified") is not True
    ]
    if unverified_labeled:
        facts.append(
            {
                "text": (
                    f"Есть {len(unverified_labeled)} элемент(ов) с сильным "
                    "authority_class без authority_verified — они не влияют "
                    "на RECOMMENDATION."
                ),
                "evidence_refs": [e["evidence_id"] for e in unverified_labeled[:5]],
            }
        )

    interpretations: list[dict[str, Any]] = []
    # Callback-style pattern: create vs navigation / read_only disagreement.
    callbackish = (
        "create_user" in (ours_t or "") + (theirs_t or "")
        or "callback" in path.lower()
        or (
            ours["read_only"] is not None
            and theirs["read_only"] is not None
            and ours["read_only"] != theirs["read_only"]
        )
    )
    if siblings and (ours["read_only"] or theirs["read_only"]):
        interpretations.append(
            {
                "mark": "inference",
                "text": (
                    "Если callback должен быть полным алиасом sibling create-path, "
                    "то read_only=True может быть дефектом."
                ),
                "evidence_refs": [e["evidence_id"] for e in siblings[:3]],
            }
        )
        interpretations.append(
            {
                "mark": "inference",
                "text": (
                    "Если callback предназначен только для существующих пользователей "
                    "(navigation), то read_only=True согласован, а create_user-ветка "
                    "может быть мёртвой/несогласованной."
                ),
                "evidence_refs": [e["evidence_id"] for e in siblings[:3]],
            }
        )
    elif only_ours and only_theirs:
        interpretations.append(
            {
                "mark": "inference",
                "text": (
                    "Уникальные изменения на обеих сторонах могут означать "
                    "разные product contracts; line-diff сам по себе не выбирает сторону."
                ),
                "evidence_refs": ["conflict_blobs"],
            }
        )
    else:
        interpretations.append(
            {
                "mark": "inference",
                "text": (
                    "Текстовое включение/совпадение строк не доказывает intended behavior."
                ),
                "evidence_refs": ["conflict_blobs"],
            }
        )

    contract_signal: dict[str, Any] | None = None
    if strong:
        top = strong[0]
        contract_signal = {
            "authority_class": top["authority_class"],
            "evidence_id": top["evidence_id"],
            "path": top["path"],
            "authority_verified": True,
            "authority_basis": top.get("authority_basis"),
            "lifecycle_status": top.get("lifecycle_status"),
            "summary_ru": (
                "Verified strong authority: "
                f"{top['path']} ({top['authority_class']}; "
                f"basis={top.get('authority_basis')}; "
                f"status={top.get('lifecycle_status')})."
            ),
            "excerpt": top.get("excerpt"),
        }

    contradictions: list[dict[str, Any]] = []
    if siblings and ours["read_only"] and theirs["read_only"]:
        if ours["read_only"] != theirs["read_only"]:
            contradictions.append(
                {
                    "text": "OURS и THEIRS расходятся по read_only.",
                    "evidence_refs": ["conflict_blobs"],
                }
            )
    if char_tests and strong:
        contradictions.append(
            {
                "text": (
                    "Characterization-тесты фиксируют текущее поведение, "
                    "а verified accepted/spec контекст может требовать другого."
                ),
                "evidence_refs": [
                    *[e["evidence_id"] for e in char_tests[:2]],
                    *[e["evidence_id"] for e in strong[:2]],
                ],
            }
        )

    # Contradictory verified authorities → null recommendation.
    polarities: dict[str, list[str]] = {}
    for e in strong:
        pol = _recommendation_polarity(e.get("excerpt") or "")
        if pol:
            polarities.setdefault(pol, []).append(e["evidence_id"])
    if len(polarities) >= 2:
        contradictions.append(
            {
                "text": (
                    "Два verified strong authority противоречат друг другу "
                    f"({', '.join(sorted(polarities))}); выбор стороны невозможен."
                ),
                "evidence_refs": [i for ids in polarities.values() for i in ids][:6],
            }
        )

    owner: list[dict[str, Any]] = []
    recommendation: dict[str, Any] | None = None

    # Recommendation ONLY from verified strong authority — never textual subset.
    if len(polarities) >= 2:
        recommendation = None
        owner.append(
            {
                "id": "contradictory_verified_authorities",
                "question": (
                    f"Какой из противоречащих verified contracts для {path} "
                    "является действующим?"
                ),
                "why_unprovable": (
                    "Два authority_verified=true источника расходятся; "
                    "порядок чтения не выбирает победителя."
                ),
                "evidence_refs": [i for ids in polarities.values() for i in ids][:6],
                "mark": "inference_gap",
            }
        )
    elif strong:
        # Per-item polarities already computed; do not join excerpts (masks conflicts).
        prefers_existing = set(polarities) == {"existing_users_only"}
        prefers_alias = set(polarities) == {"full_alias"}
        why_accepted = "; ".join(
            f"{e['path']}: {e.get('authority_basis')} "
            f"(status={e.get('lifecycle_status')})"
            for e in strong[:3]
        )
        if prefers_existing and not prefers_alias:
            prefer_side = None
            if ours["read_only"] == "True" and theirs["read_only"] != "True":
                prefer_side = "keep_ours"
            elif theirs["read_only"] == "True" and ours["read_only"] != "True":
                prefer_side = "keep_theirs"
            if prefer_side:
                recommendation = {
                    "option_id": prefer_side,
                    "rationale": (
                        "Verified accepted/current contract указывает "
                        "existing-users-only; сторона с read_only=True согласована. "
                        f"Почему accepted: {why_accepted}. "
                        "Файлы не изменялись."
                    ),
                    "evidence_refs": [e["evidence_id"] for e in strong[:5]],
                    "strength": "verified_strong_authority",
                    "authority_basis": why_accepted,
                }
            else:
                recommendation = {
                    "option_id": "align_to_contract",
                    "rationale": (
                        "Есть verified репозиторный контракт; реализацию нужно "
                        "выровнять вручную. "
                        f"Почему accepted: {why_accepted}."
                    ),
                    "evidence_refs": [e["evidence_id"] for e in strong[:5]],
                    "strength": "verified_strong_authority",
                    "authority_basis": why_accepted,
                }
        elif prefers_alias and not prefers_existing:
            prefer_side = None
            if ours["read_only"] == "False" and theirs["read_only"] != "False":
                prefer_side = "keep_ours"
            elif theirs["read_only"] == "False" and ours["read_only"] != "False":
                prefer_side = "keep_theirs"
            if prefer_side:
                recommendation = {
                    "option_id": prefer_side,
                    "rationale": (
                        "Verified contract указывает полный alias create-path; "
                        "сторона с read_only=False согласована. "
                        f"Почему accepted: {why_accepted}."
                    ),
                    "evidence_refs": [e["evidence_id"] for e in strong[:5]],
                    "strength": "verified_strong_authority",
                    "authority_basis": why_accepted,
                }
        if recommendation is None and len(polarities) < 2:
            owner.append(
                {
                    "id": "contract_present_but_ambiguous",
                    "question": (
                        f"Какой контракт для {path} следует из "
                        f"{strong[0]['path']} и как его применить к OURS/THEIRS?"
                    ),
                    "why_unprovable": (
                        "Verified authority найден, но не различает стороны "
                        "однозначно по наблюдаемым признакам."
                    ),
                    "evidence_refs": [e["evidence_id"] for e in strong[:3]],
                    "mark": "inference_gap",
                }
            )
    else:
        if callbackish:
            owner.append(
                {
                    "id": "callback_contract_choice",
                    "question": (
                        f"Какой контракт у callback в {path}: "
                        "полный алиас create-path (/start) или navigation "
                        "только для существующих пользователей?"
                    ),
                    "why_unprovable": (
                        "Sibling/test evidence не является нормативной authority; "
                        "accepted decision/spec не найдены в бюджете."
                    ),
                    "evidence_refs": [
                        *[e["evidence_id"] for e in siblings[:2]],
                        *[e["evidence_id"] for e in tests[:2]],
                    ],
                    "mark": "inference_gap",
                }
            )
        else:
            owner.append(
                {
                    "id": "product_contract_choice",
                    "question": (
                        f"Какой контракт поведения должен остаться для {path}?"
                    ),
                    "why_unprovable": (
                        "Нет ACCEPTED_DECISION/CURRENT_SPEC/CONTRACT/API_INVARIANT; "
                        "текстовый subset/sibling similarity не являются authority."
                    ),
                    "evidence_refs": ["conflict_blobs"],
                    "mark": "inference_gap",
                }
            )
        recommendation = None

    options = [
        {
            "id": "keep_ours",
            "title": "Оставить сторону OURS",
            "behavior_after": ours["summary_ru"],
            "retained_from_ours": "Содержимое stage 2",
            "retained_from_theirs": "ничего",
            "supporting_evidence": [],
            "contradicting_evidence": [e["evidence_id"] for e in strong[:3]]
            if recommendation and recommendation.get("option_id") == "keep_theirs"
            else [],
            "risk": "Потеря изменений THEIRS; возможное расхождение с sibling/контрактом.",
            "validation_needed": [f"Проверить поведение {path} после выбора OURS"],
        },
        {
            "id": "keep_theirs",
            "title": "Оставить сторону THEIRS",
            "behavior_after": theirs["summary_ru"],
            "retained_from_ours": "ничего",
            "retained_from_theirs": "Содержимое stage 3",
            "supporting_evidence": [],
            "contradicting_evidence": [e["evidence_id"] for e in strong[:3]]
            if recommendation and recommendation.get("option_id") == "keep_ours"
            else [],
            "risk": "Потеря изменений OURS; возможное расхождение с текущей веткой.",
            "validation_needed": [f"Проверить поведение {path} после выбора THEIRS"],
        },
        {
            "id": "manual_combine",
            "title": "Вручную скомбинировать стороны под выбранный контракт",
            "behavior_after": "Поведение после явного объединения фрагментов Owner.",
            "retained_from_ours": "Выбранные фрагменты",
            "retained_from_theirs": "Выбранные фрагменты",
            "supporting_evidence": [e["evidence_id"] for e in strong[:3]],
            "contradicting_evidence": [],
            "risk": "Ошибочная комбинация; требует проверки Owner.",
            "validation_needed": [
                "Точечные тесты вокруг изменённых символов",
                "Проверка согласованности со sibling/контрактом",
            ],
        },
    ]
    if recommendation and recommendation.get("option_id") == "align_to_contract":
        options.append(
            {
                "id": "align_to_contract",
                "title": "Выровнять реализацию под явный репозиторный контракт",
                "behavior_after": recommendation["rationale"],
                "retained_from_ours": "Только согласованное с контрактом",
                "retained_from_theirs": "Только согласованное с контрактом",
                "supporting_evidence": recommendation.get("evidence_refs") or [],
                "contradicting_evidence": [e["evidence_id"] for e in char_tests[:3]],
                "risk": "Characterization-тесты могут потребовать обновления.",
                "validation_needed": [
                    "Обновить/добавить contract tests под accepted decision",
                    "Проверить мёртвые ветки (например create_user)",
                ],
            }
        )

    disagreement_ru = (
        "Стороны расходятся по наблюдаемому поведению "
        f"(уникальных строк ours={len(only_ours)}, theirs={len(only_theirs)}). "
    )
    if ours["read_only"] != theirs["read_only"]:
        disagreement_ru += (
            f"Различие read_only: OURS={ours['read_only']} vs "
            f"THEIRS={theirs['read_only']}. "
        )
    if siblings:
        disagreement_ru += (
            "Sibling-код показывает иной/похожий API-паттерн, но не является нормой. "
        )
    if not strong:
        disagreement_ru += (
            "Авторитетный контракт в бюджете не найден — выбор стороны требует Owner."
        )
    else:
        disagreement_ru += "Есть авторитетный контекст; см. CONTRACT_SIGNAL."

    short_ru = (
        f"Конфликт в «{path}»: нужно понять, какое поведение согласовано с "
        "остальным проектом. Изменения не применялись."
    )

    return {
        "SHORT_RU": short_ru,
        "FACTS": facts,
        "OURS": ours,
        "THEIRS": theirs,
        "DISAGREEMENT_RU": disagreement_ru,
        "INTERPRETATIONS": interpretations,
        "CONTRACT_SIGNAL": contract_signal,
        "CONTRADICTIONS": contradictions,
        "OWNER_DECISIONS_REQUIRED": owner,
        "RESOLUTION_OPTIONS": options,
        "RECOMMENDATION": recommendation,
        "CHARACTERIZATION_TESTS": [
            {"evidence_id": e["evidence_id"], "path": e["path"], "kind": e.get("test_kind")}
            for e in char_tests
        ],
        "CONTRACT_TESTS": [
            {"evidence_id": e["evidence_id"], "path": e["path"], "kind": e.get("test_kind")}
            for e in contract_tests
        ],
        "TEXTUAL_SUBSET_NOTE": (
            "Текстовое включение/line-set equivalence никогда не создаёт "
            "рекомендацию keep_ours/keep_theirs."
        ),
    }


def _human_report_ru(report: dict[str, Any]) -> str:
    """Render Russian human-readable advisory report (behavior first)."""
    lines: list[str] = [SAFETY_LABEL_RU, ""]
    lines.append("## Коротко")
    lines.append(str(report.get("SHORT_RU") or ""))
    lines.append("")
    lines.append("## Факты")
    for fact in report.get("FACTS") or []:
        if isinstance(fact, dict):
            refs = ",".join(fact.get("evidence_refs") or [])
            suffix = f" [{refs}]" if refs else ""
            lines.append(f"- {fact.get('text')}{suffix}")
        else:
            lines.append(f"- {fact}")
    lines.append("")
    ours = report.get("OURS") or {}
    theirs = report.get("THEIRS") or {}
    lines.append("## Что делает OURS")
    lines.append(str(ours.get("summary_ru") if isinstance(ours, dict) else ours))
    lines.append("")
    lines.append("## Что делает THEIRS")
    lines.append(str(theirs.get("summary_ru") if isinstance(theirs, dict) else theirs))
    lines.append("")
    lines.append("## Контекст репозитория")
    ctx = report.get("CONTEXT_EVIDENCE") or {}
    for e in (ctx.get("evidence") or [])[:12]:
        lines.append(
            f"- [{e.get('evidence_id')}] {e.get('authority_class')} "
            f"{e.get('path')}:{e.get('line_start')}-{e.get('line_end')} — "
            f"{e.get('match_reason')}"
        )
    gaps = ctx.get("evidence_gaps") or []
    if gaps:
        lines.append("Пробелы evidence:")
        for g in gaps:
            lines.append(f"- EVIDENCE_GAP: {g}")
    lines.append("")
    lines.append("## В чём реальное расхождение")
    lines.append(str(report.get("DISAGREEMENT_RU") or report.get("SEMANTIC_CONFLICT") or ""))
    lines.append("")
    lines.append("## Интерпретации")
    for item in report.get("INTERPRETATIONS") or []:
        refs = ",".join(item.get("evidence_refs") or [])
        suffix = f" [{refs}]" if refs else ""
        lines.append(f"- [{item.get('mark')}] {item.get('text')}{suffix}")
    lines.append("")
    lines.append("## Вопросы владельцу")
    decisions = report.get("OWNER_DECISIONS_REQUIRED") or []
    if not decisions:
        lines.append("- Нет обязательного Owner-вопроса по текущим фактам.")
    else:
        for d in decisions:
            lines.append(f"- {d.get('question')}")
    lines.append("")
    lines.append("## Варианты")
    for opt in report.get("RESOLUTION_OPTIONS") or []:
        lines.append(f"### {opt.get('id')}: {opt.get('title')}")
        lines.append(str(opt.get("behavior_after") or opt.get("resulting_behavior") or ""))
        if opt.get("risk"):
            lines.append(f"Риск: {opt.get('risk')}")
    lines.append("")
    rec = report.get("RECOMMENDATION")
    lines.append("## Рекомендация")
    if rec is None:
        lines.append(
            "RECOMMENDATION=null — недостаточно сильного репозиторного authority, "
            "чтобы выбрать сторону. Нужно решение Owner."
        )
    else:
        lines.append(f"Предпочтительный вариант: {rec.get('option_id')}")
        lines.append(str(rec.get("rationale") or ""))
        refs = ",".join(rec.get("evidence_refs") or [])
        if refs:
            lines.append(f"Evidence: {refs}")
    lines.append("")
    lines.append("## Как проверить")
    for step in report.get("VALIDATION_PLAN") or []:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Ограничения")
    for lim in report.get("LIMITATIONS") or []:
        lines.append(f"- {lim}")
    lines.append("")
    # Low-level Git details last.
    cur = report.get("CURRENT_CONFLICT") or {}
    lines.append("## Технические детали Git (ниже объяснения)")
    lines.append(f"Операция: {cur.get('operation')}")
    lines.append(f"Путь: {cur.get('path')}")
    ids = cur.get("stage_blob_identities") or {}
    lines.append(f"Stage OIDs: base={ids.get('1')} ours={ids.get('2')} theirs={ids.get('3')}")
    mut = report.get("MUTATION_ASSERTION") or {}
    lines.append(
        f"Неизменность: worktree={mut.get('worktree_unchanged')} "
        f"index={mut.get('index_unchanged')} refs={mut.get('refs_unchanged')}"
    )
    return "\n".join(lines) + "\n"


def run_preview_advisory(
    repo_root: Path,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Run Windows PREVIEW_ONLY advisory analysis; return report dict.

    Analyzes exactly one conflicted path per invocation (R40). When ``path``
    is omitted and multiple unmerged paths exist, raises
    ``PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS``.

    Raises:
        StopRequired: typed fail-closed conditions (platform, no conflict,
            multi-path without ``--path``, mutation, context path
            escape/symlink, etc.).
    """
    assert_supported_platform()
    repo = Path(repo_root).resolve()
    git = PreviewReadonlyGit(repo)
    try:
        operation = _detect_operation(git)
        probe = git.read_unmerged_index()
        probe_rows = _parse_unmerged(probe or "")
        if not probe_rows:
            raise StopRequired("PREVIEW_NO_UNMERGED_PATHS")
        all_paths = sorted({row[3] for row in probe_rows})
        selected_path = _select_preview_path(all_paths, path=path)
        focus_paths = [selected_path]
        before = _capture_state(git, paths=focus_paths)
        snapshots = _load_conflict_paths(git, path_filter=selected_path)
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

        stage_oids = {
            "1": base_b.oid if base_b else None,
            "2": ours_b.oid if ours_b else None,
            "3": theirs_b.oid if theirs_b else None,
        }
        context = collect_conflict_context(
            repo,
            conflict_path=primary.path,
            operation=operation,
            base_text=base_t,
            ours_text=ours_t,
            theirs_text=theirs_t,
            stage_oids=stage_oids,
        )
        reasoning = _build_advisory_reasoning(
            path=primary.path,
            ours_t=ours_t,
            theirs_t=theirs_t,
            context=context,
        )

        validation_plan = [
            f"Точечные тесты для символов в {primary.path}",
            "Сверить выбор со sibling/контрактом из CONTEXT_EVIDENCE",
            "При изменении characterization-тестов — явно зафиксировать новый контракт",
        ]
        limitations = [
            "Результат advisory; требуется проверка человеком.",
            "Изменения не применялись и не должны применяться автоматически.",
            "Sibling-код и characterization-тесты — evidence, не нормативная authority.",
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

        # Compatibility aliases for prior report consumers.
        fact_strings = [
            f["text"] if isinstance(f, dict) else str(f) for f in reasoning["FACTS"]
        ]
        fact_strings.append(f"Операция Git: {operation}")
        fact_strings.append(reasoning["TEXTUAL_SUBSET_NOTE"])

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
                # Inventory of unmerged paths in the repo — not analysis coverage.
                "unmerged_paths_inventory": all_paths,
                "all_unmerged_paths": all_paths,
                "all_unmerged_paths_role": "inventory_not_analyzed",
                "stage_blob_identities": stage_oids,
                "base_available": base_b is not None,
                "ours_available": ours_b is not None,
                "theirs_available": theirs_b is not None,
            },
            "SHORT_RU": reasoning["SHORT_RU"],
            "FACTS": reasoning["FACTS"],
            "FACTS_TEXT": fact_strings,
            "OURS": reasoning["OURS"],
            "THEIRS": reasoning["THEIRS"],
            "DISAGREEMENT_RU": reasoning["DISAGREEMENT_RU"],
            "SEMANTIC_CONFLICT": reasoning["DISAGREEMENT_RU"],
            "CONTEXT": {
                "paths_analyzed": [primary.path],
                "note": (
                    "R40: semantic analysis covers exactly one selected path. "
                    "CURRENT_CONFLICT.unmerged_paths_inventory / "
                    "all_unmerged_paths are inventory only, not analysis coverage."
                ),
            },
            "CONTEXT_EVIDENCE": context,
            "INTERPRETATIONS": reasoning["INTERPRETATIONS"],
            "CONTRACT_SIGNAL": reasoning["CONTRACT_SIGNAL"],
            "CONTRADICTIONS": reasoning["CONTRADICTIONS"],
            "OWNER_DECISIONS_REQUIRED": reasoning["OWNER_DECISIONS_REQUIRED"],
            "RESOLUTION_OPTIONS": reasoning["RESOLUTION_OPTIONS"],
            "RECOMMENDATION": reasoning["RECOMMENDATION"],
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
    except Exception as exc:  # noqa: BLE001 — convert to typed STOP
        raise StopRequired(
            "PREVIEW_UNEXPECTED_EXCEPTION",
            {
                "error": type(exc).__name__,
                "detail": str(exc)[:400],
            },
        ) from exc
