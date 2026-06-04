"""Слияние V3Action buckets (legacy NO_DATA / shelf promotion tests)."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)


def merge_and_dedup_actions(
    cleanup_actions: list[V3Action],
    m1_actions: list[V3Action],
    m2_actions: list[V3Action],
    m3_actions: list[V3Action],
) -> list[V3Action]:
    """Слить действия с приоритетом cleanup > M2 > M1 > M3 по ``keyword_setting_id``.

    Внутри одного входного списка все действия для одного ключа сохраняются
    (например N-state: FORCE_OFF → UP). Между списками для ключа побеждает bucket
    более высокого приоритета целиком — все его действия по этому ключу.
    """
    buckets: list[list[V3Action]] = [
        m3_actions,
        m1_actions,
        m2_actions,
        cleanup_actions,
    ]
    winner_bucket: dict[int, int] = {}
    for bidx, bucket in enumerate(buckets):
        for action in bucket:
            if action.action == V3ActionType.DO_NOTHING:
                continue
            ks_id = action.keyword_setting_id
            if ks_id is None:
                continue
            winner_bucket[int(ks_id)] = bidx

    result: list[V3Action] = []
    for bidx, bucket in enumerate(buckets):
        for action in bucket:
            if action.action == V3ActionType.DO_NOTHING:
                continue
            ks_id = action.keyword_setting_id
            if ks_id is None:
                result.append(action)
                continue
            if winner_bucket.get(int(ks_id)) == bidx:
                result.append(action)
    return result
