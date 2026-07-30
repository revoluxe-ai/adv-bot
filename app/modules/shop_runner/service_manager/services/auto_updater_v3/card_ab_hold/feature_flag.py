"""Fail-closed feature flag / allowlist для epoch-managed A/B Hold (§25 / OD-05).

Новая lifecycle (phase non-NULL) MUST NOT включаться по умолчанию. Broad enable
для всех paid — только после OD-05; до этого — env flag + явный allowlist.

Spec requirement: «Broad enablement is gated behind owner manual test, limited
beta, and an explicit owner decision» — см. ``evaluate_card_ab_hold_broad_enable_readiness``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


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

    Spec: Broad enablement is gated behind owner manual test, limited beta,
    and an explicit owner decision (OD-05).
    """
    return _parse_truthy(os.environ.get("CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED"))


@dataclass(frozen=True)
class CardAbHoldBroadEnableReadiness:
    """Снимок readiness перед снятием ограничения broad enable (§25 / OD-05).

    ``broad_enable_allowed`` истинно **только** при принятом OD-05.
    Master flag и allowlist сами по себе не открывают всех paid-пользователей.
    """

    od05_accepted: bool
    epoch_master_flag_enabled: bool
    allowlist_adv_count: int
    allowlist_shop_count: int
    broad_enable_allowed: bool
    blocking_reasons: tuple[str, ...]


def evaluate_card_ab_hold_broad_enable_readiness() -> CardAbHoldBroadEnableReadiness:
    """Проверка readiness перед снятием ограничения broad enable (OD-05).

    Spec requirement: «Broad enablement is gated behind owner manual test,
    limited beta, and an explicit owner decision».

    Allowlist / master flag — limited beta / pilot, не broad. Без
    ``CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED`` результат всегда
    ``broad_enable_allowed=False``.

    Returns:
        Иммутабельный снимок текущего env-состояния и blocking reasons.
    """
    od05 = is_card_ab_hold_broad_enable_authorized()
    master = is_card_ab_hold_epoch_flow_enabled()
    adv_count = len(card_ab_hold_epoch_allowlist_adv_ids())
    shop_count = len(card_ab_hold_epoch_allowlist_shop_ids())
    reasons: list[str] = []
    if not od05:
        reasons.append(
            "OD-05 not accepted "
            "(CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED unset/false)"
        )
    return CardAbHoldBroadEnableReadiness(
        od05_accepted=od05,
        epoch_master_flag_enabled=master,
        allowlist_adv_count=adv_count,
        allowlist_shop_count=shop_count,
        broad_enable_allowed=od05,
        blocking_reasons=tuple(reasons),
    )


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
