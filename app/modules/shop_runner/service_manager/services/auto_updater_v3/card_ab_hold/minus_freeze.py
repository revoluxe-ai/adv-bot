"""A/B Hold: freeze разрешённого набора фраз (allowed-set) + enforcement (decision §8).

Primary invariant spec ``card-ab-hold-mode``: замораживается **разрешённый**
(relevant/GOOD) набор фраз кампании, а не список минус-фраз. Минус — производный
механизм исключения: во время hold любые новые/не-разрешённые фразы исключаются
(минусуются), а разрешённые фразы, снятые вручную, восстанавливаются. Enforcement
ограничен лимитом WB (~1000 фраз/nmid); при превышении — **видимая деградация**
(caller MUST не заявлять чистый hold молча).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any, TypedDict, cast

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
    normalize_card_ab_hold_mode,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.shared.domains.wb.utils.wb_campaign_meta import (
    wb_campaign_meta_known,
    wb_is_manual_shelf_only,
    wb_supports_normquery_minus_phrases,
)

logger = logging.getLogger(__name__)

GetMinusFn = Callable[[int, int], Awaitable[list[str]]]
SetMinusFn = Callable[[int, int, list[str]], Awaitable[Any]]
GetObservedTextsFn = Callable[[int, int], Awaitable[list[str]]]

# WB лимит минус-фраз на nmid (normquery set-minus). Если для удержания
# замороженного allowed-set нужно исключить больше фраз — enforcement не может
# гарантировать чистый hold → видимая деградация (см. ``enforce_allowed_set``).
WB_MINUS_CAP = 1000

# Spec scenario: Manual bot minus update does not report success during freeze.
AB_HOLD_MANUAL_MINUS_UPDATE_BLOCKED_MSG = (
    "Минус-слова не обновлены: при A/B Hold набор фраз зафиксирован. "
    "Чтобы изменить набор фраз, отключите A/B Hold."
)
MINUS_PHRASES_UPDATED_SUCCESS_MSG = "Минус-слова обновлены."


def user_message_after_ordinary_minus_update(*, applied: bool) -> str:
    """Telegram copy после ordinary ``update_minus_phrases`` (spec §10 / decision §8).

    Args:
        applied: True если ordinary sync реально выполнялся; False при freeze skip.

    Returns:
        Success или blocked-сообщение; silent no-op с success Forbidden.
    """
    if applied:
        return MINUS_PHRASES_UPDATED_SUCCESS_MSG
    return AB_HOLD_MANUAL_MINUS_UPDATE_BLOCKED_MSG


class AbHoldEnforceResult(TypedDict):
    """Итог enforcement allowed-set по всем (adv_id, nmid) целям hold.

    Attributes:
        targets: сколько (adv_id, nmid) целей обработано.
        written: сколько целей потребовало set-minus write (drift).
        cap_exceeded: цели, где не-разрешённых фраз > WB_MINUS_CAP (hold degraded).
    """

    targets: int
    written: int
    cap_exceeded: list[tuple[int, int]]


def empty_allowed_snapshot() -> list[str]:
    """Пустой allowed-set snapshot (EXIT / default)."""
    return []


def normalize_allowed_snapshot(raw: object | None) -> list[str]:
    """Нормализовать JSONB allowed-set к отсортированному списку уникальных строк.

    Args:
        raw: значение из PG / in-memory (list|tuple|set|None|прочее).

    Returns:
        Отсортированные уникальные непустые тексты; иное → [].
    """
    if not isinstance(raw, (list, tuple, set)):
        return []
    out: set[str] = set()
    for item in cast(Iterable[object], raw):
        if item is None:
            continue
        text = str(item)
        if text:
            out.add(text)
    return sorted(out)


def capture_allowed_phrase_set(keywords: Sequence[Any]) -> list[str]:
    """Зафиксировать разрешённый набор фраз на ENTER (spec §8, primary invariant).

    Allowed = тексты ключей со статусом != BAD (GOOD / недостаточно показов):
    именно этим фразам разрешено тратить. Всё остальное (BAD, не-релевантные,
    новые после ENTER) во время hold исключается как производный минус.

    Args:
        keywords: ``CalculatedKeyword``-подобные объекты с ``.status`` и ``.text``.

    Returns:
        Отсортированные уникальные разрешённые тексты фраз.
    """
    allowed: set[str] = set()
    for kw in keywords:
        if getattr(kw, "status", None) == KeywordStatus.BAD:
            continue
        text = str(getattr(kw, "text", "") or "")
        if text:
            allowed.add(text)
    return sorted(allowed)


def compute_enforced_minus(
    observed_texts: Sequence[str],
    allowed_texts: Sequence[str],
) -> tuple[list[str], bool]:
    """Целевой минус для одного nmid = наблюдаемые фразы вне allowed-set.

    Args:
        observed_texts: фразы, которые могут тратить (кластерные тексты + текущий минус).
        allowed_texts: замороженный разрешённый набор.

    Returns:
        (capped_minus, cap_exceeded). ``capped_minus`` отсортирован и обрезан до
        ``WB_MINUS_CAP``; ``cap_exceeded`` True, если не-разрешённых фраз больше cap
        — caller MUST деградировать видимо (не заявлять чистый hold).
    """
    allowed_set = set(allowed_texts)
    non_allowed = sorted({str(t) for t in observed_texts if str(t)} - allowed_set)
    return non_allowed[:WB_MINUS_CAP], len(non_allowed) > WB_MINUS_CAP


def should_skip_ordinary_minus_recalculation(mode: CardAbHoldMode | str | None) -> bool:
    """Ordinary ``update_minus_phrases`` recalc (меняющий allowed-set) MUST NOT при freeze."""
    return is_ab_hold_structural_freeze(mode)


def is_ab_hold_ready_for_tests(mode: CardAbHoldMode | str | None) -> bool:
    """UI «можно запускать A/B» только при ACTIVE после полного setup."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.ACTIVE


def iter_minus_phrase_wb_targets(complex_adv: Any) -> list[tuple[int, int]]:
    """Пары (adv_id, nmid) для enforcement, зеркало skip-логики MinusPhraseManager.

    Auto: skip только ``wb_is_manual_shelf_only``.
    Search: skip если meta known и не supports normquery.
    """
    targets: list[tuple[int, int]] = []
    adv_setting = complex_adv.adv_setting
    if not wb_is_manual_shelf_only(adv_setting):
        auto_id = int(complex_adv.auto_adv_id)
        for nmid in list(getattr(adv_setting, "nmids", None) or []):
            targets.append((auto_id, int(nmid)))
    search_adv = getattr(complex_adv, "search_adv", None)
    if search_adv is not None:
        if not (
            wb_campaign_meta_known(search_adv)
            and not wb_supports_normquery_minus_phrases(search_adv)
        ):
            search_id = int(search_adv.adv_id)
            for nmid in list(getattr(search_adv, "nmids", None) or []):
                targets.append((search_id, int(nmid)))
    return targets


async def enforce_allowed_set(
    complex_adv: Any,
    *,
    allowed: object | None,
    get_minus: GetMinusFn,
    set_minus: SetMinusFn,
    get_observed: GetObservedTextsFn,
) -> AbHoldEnforceResult:
    """Привести WB-минус каждого (adv_id, nmid) к «всё вне замороженного allowed-set».

    Hold-protection (отдельно от ordinary recalc): наблюдаемые фразы (кластерные
    тексты ∪ текущий минус) вне allowed-set исключаются; разрешённые фразы, снятые
    вручную, восстанавливаются (их нет в целевом минусе, поэтому set-minus их убирает).
    Ограничено ``WB_MINUS_CAP``; превышение — видимая деградация (log ERROR +
    ``cap_exceeded``), hold не гарантирован для такой РК.

    Args:
        complex_adv: РК для перечисления (adv_id, nmid) целей.
        allowed: замороженный allowed-set (JSONB list или нормализуемое значение).
        get_minus: чтение текущих минус-фраз WB для (adv_id, nmid).
        set_minus: запись минус-фраз WB для (adv_id, nmid).
        get_observed: наблюдаемые кластерные тексты для (adv_id, nmid).

    Returns:
        ``AbHoldEnforceResult`` с числом целей/записей и списком cap-degraded целей.
    """
    allowed_texts = normalize_allowed_snapshot(allowed)
    allowed_set = set(allowed_texts)
    targets = iter_minus_phrase_wb_targets(complex_adv)
    written = 0
    cap_exceeded: list[tuple[int, int]] = []
    for adv_id, nmid in targets:
        current = [str(p) for p in await get_minus(adv_id, nmid)]
        observed = [str(p) for p in await get_observed(adv_id, nmid)]
        universe = set(observed) | set(current)
        desired, exceeded = compute_enforced_minus(sorted(universe), allowed_texts)
        if exceeded:
            cap_exceeded.append((adv_id, nmid))
            logger.error(
                "[adv_id=%s] ab_hold allowed-set enforcement exceeds WB minus cap "
                "nmid=%s non_allowed=%s cap=%s: hold NOT guaranteed clean (degraded)",
                adv_id,
                nmid,
                len(universe - allowed_set),
                WB_MINUS_CAP,
            )
        if set(desired) != set(current):
            await set_minus(adv_id, nmid, list(desired))
            written += 1
            logger.info(
                "[adv_id=%s] ab_hold enforce nmid=%s minus=%s allowed=%s observed=%s",
                adv_id,
                nmid,
                len(desired),
                len(allowed_set),
                len(universe),
            )
    return {"targets": len(targets), "written": written, "cap_exceeded": cap_exceeded}
