"""A/B Hold freeze минус-фраз: PG snapshot, drift detect, restore (decision §8).

Spec ``card-ab-hold-mode``: ENTER sync → snapshot → ACTIVE; PENDING/ACTIVE —
без ordinary recalculation; drift → restore; EXIT — clear snapshot.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypedDict, cast

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
    normalize_card_ab_hold_mode,
)
from app.shared.domains.wb.utils.wb_campaign_meta import (
    wb_campaign_meta_known,
    wb_is_manual_shelf_only,
    wb_supports_normquery_minus_phrases,
)

logger = logging.getLogger(__name__)

GetMinusFn = Callable[[int, int], Awaitable[list[str]]]
SetMinusFn = Callable[[int, int, list[str]], Awaitable[Any]]


class MinusSnapshotEntry(TypedDict):
    """Одна запись snapshot: минус-фразы для пары (adv_id, nmid)."""

    adv_id: int
    nmid: int
    phrases: list[str]


def empty_minus_snapshot() -> list[MinusSnapshotEntry]:
    """Пустой snapshot (EXIT / default)."""
    return []


def _as_int(value: object) -> int:
    """Привести object к int или raise TypeError/ValueError."""
    if isinstance(value, bool):
        raise TypeError("bool is not a valid int for snapshot ids")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"unsupported snapshot id type: {type(value)!r}")


def normalize_minus_snapshot(raw: object | None) -> list[MinusSnapshotEntry]:
    """Нормализовать JSONB snapshot к списку записей.

    Args:
        raw: значение из PG / in-memory (list|None|прочее).

    Returns:
        Валидные ``MinusSnapshotEntry``; битые элементы отбрасываются.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    raw_list = cast(list[object], raw)
    out: list[MinusSnapshotEntry] = []
    for item_obj in raw_list:
        if not isinstance(item_obj, dict):
            continue
        item = cast(dict[str, object], item_obj)
        try:
            adv_id = _as_int(item["adv_id"])
            nmid = _as_int(item["nmid"])
        except (KeyError, TypeError, ValueError):
            continue
        phrases_obj = item.get("phrases", [])
        phrases: list[str] = []
        if isinstance(phrases_obj, list):
            phrases_list = cast(list[object], phrases_obj)
            for p in phrases_list:
                if p is None:
                    continue
                text = str(p)
                if text:
                    phrases.append(text)
            phrases = sorted(set(phrases))
        out.append({"adv_id": adv_id, "nmid": nmid, "phrases": phrases})
    return out


def minus_phrases_drift(current: Sequence[str], snapshot: Sequence[str]) -> bool:
    """True, если текущий набор минус-фраз отличается от snapshot."""
    return set(current) != set(snapshot)


def should_skip_ordinary_minus_recalculation(mode: CardAbHoldMode | str | None) -> bool:
    """Ordinary ``update_minus_phrases`` MUST NOT при PENDING_SETUP / ACTIVE."""
    return is_ab_hold_structural_freeze(mode)


def is_ab_hold_ready_for_tests(mode: CardAbHoldMode | str | None) -> bool:
    """UI «можно запускать A/B» только при ACTIVE после полного setup."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.ACTIVE


def iter_minus_phrase_wb_targets(complex_adv: Any) -> list[tuple[int, int]]:
    """Пары (adv_id, nmid) для capture/restore, зеркало skip-логики MinusPhraseManager.

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


async def capture_minus_snapshot(
    complex_adv: Any,
    *,
    get_minus: GetMinusFn,
) -> list[MinusSnapshotEntry]:
    """Считать текущие минус-фразы с WB и собрать PG snapshot.

    Spec ENTER: после setup-sync сохранить актуальное состояние.
    """
    entries: list[MinusSnapshotEntry] = []
    for adv_id, nmid in iter_minus_phrase_wb_targets(complex_adv):
        phrases = await get_minus(adv_id, nmid)
        entries.append(
            {
                "adv_id": adv_id,
                "nmid": nmid,
                "phrases": sorted({str(p) for p in phrases}),
            }
        )
    return entries


async def restore_minus_snapshot_if_drift(
    complex_adv: Any,
    *,
    snapshot: object | None,
    get_minus: GetMinusFn,
    set_minus: SetMinusFn,
) -> int:
    """Вернуть WB к snapshot при drift. Returns: число restore-write.

    Spec HOLD: ручные правки = нарушение freeze → overwrite.
    """
    entries = normalize_minus_snapshot(snapshot)
    if not entries:
        return 0
    restored = 0
    for entry in entries:
        adv_id = entry["adv_id"]
        nmid = entry["nmid"]
        expected = entry["phrases"]
        current = await get_minus(adv_id, nmid)
        if not minus_phrases_drift(current, expected):
            continue
        await set_minus(adv_id, nmid, list(expected))
        restored += 1
        logger.info(
            "[adv_id=%s] ab_hold minus restore nmid=%s phrases=%s",
            adv_id,
            nmid,
            len(expected),
        )
    return restored
