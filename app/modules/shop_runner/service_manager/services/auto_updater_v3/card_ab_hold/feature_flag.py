"""Fail-closed feature flag / allowlist для epoch-managed A/B Hold (§25 / OD-05).

Новая lifecycle (phase non-NULL) MUST NOT включаться по умолчанию. Broad enable
для всех paid — только после OD-05; до этого — env flag + явный allowlist.
"""

from __future__ import annotations

import os
from typing import Iterable


def _parse_truthy(raw: str | None) -> bool:
    """Разбор fail-closed bool env (пусто / unknown → False)."""
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _parse_id_set(raw: str | None) -> frozenset[int]:
    """CSV целых id; битый токен пропускается (не открывает flow)."""
    if not raw or not str(raw).strip():
        return frozenset()
    out: set[int] = set()
    for part in str(raw).split(","):
        token = part.strip()
        if not token:
            continue
        try:
            out.add(int(token))
        except ValueError:
            continue
    return frozenset(out)


def is_card_ab_hold_epoch_flow_enabled() -> bool:
    """Глобальный master-switch epoch-managed flow (default OFF).

    Env: ``CARD_AB_HOLD_EPOCH_FLOW_ENABLED`` (1/true/yes/on).
    """
    return _parse_truthy(os.environ.get("CARD_AB_HOLD_EPOCH_FLOW_ENABLED"))


def card_ab_hold_epoch_allowlist_adv_ids() -> frozenset[int]:
    """Allowlist ``adv_id`` для epoch-managed enable (пусто = никто).

    Env: ``CARD_AB_HOLD_EPOCH_ALLOWLIST_ADV_IDS`` — CSV ints.
    """
    return _parse_id_set(os.environ.get("CARD_AB_HOLD_EPOCH_ALLOWLIST_ADV_IDS"))


def card_ab_hold_epoch_allowlist_shop_ids() -> frozenset[int]:
    """Allowlist ``shop_id`` для epoch-managed enable (пусто = никто).

    Env: ``CARD_AB_HOLD_EPOCH_ALLOWLIST_SHOP_IDS`` — CSV ints.
    """
    return _parse_id_set(os.environ.get("CARD_AB_HOLD_EPOCH_ALLOWLIST_SHOP_IDS"))


def coerce_shop_id_for_epoch_allowlist(raw: object | None) -> int | None:
    """Нормализовать ``WBCabinet.shop_id`` (str) к int для allowlist.

    Non-numeric / empty / bool → ``None`` (fail-closed shop hit, без crash).
    ``AdvSetting`` не имеет колонки ``shop_id``; источник — joined relation.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return int(raw)
    try:
        text = str(raw).strip()
    except Exception:
        return None
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def is_card_ab_hold_broad_enable_authorized() -> bool:
    """OD-05 gate: broad enable без явного env MUST оставаться False.

    Env: ``CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED`` (default unset → False).
    """
    return _parse_truthy(os.environ.get("CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED"))


def can_enter_epoch_managed_ab_hold(
    *,
    adv_id: int,
    shop_id: int | None = None,
) -> bool:
    """Разрешён ли вход в epoch-managed flow для кампании (fail-closed).

    Правила (§25):
    - master flag OFF → False;
    - OD-05 принят → True для всех (broad);
    - иначе нужен hit allowlist по ``adv_id`` и/или ``shop_id``;
    - пустой allowlist при flag ON → всё равно False (нет silent open).
    """
    if not is_card_ab_hold_epoch_flow_enabled():
        return False
    if is_card_ab_hold_broad_enable_authorized():
        return True
    if int(adv_id) in card_ab_hold_epoch_allowlist_adv_ids():
        return True
    if shop_id is not None and int(shop_id) in card_ab_hold_epoch_allowlist_shop_ids():
        return True
    return False


def assert_allowlist_ids(ids: Iterable[int]) -> frozenset[int]:
    """Тестовый хелпер: нормализовать набор id без чтения env."""
    return frozenset(int(x) for x in ids)
