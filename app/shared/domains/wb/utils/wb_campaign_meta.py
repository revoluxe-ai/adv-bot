"""Снимок типа РК и зон показа WB для AdvSetting (sync из v2/adverts).

Контекст для ревью (минус-фразы и normquery API)
=================================================

WB ``POST /adv/v0/normquery/set-minus`` и ``get-minus`` принимают **только**
кампании с **ручной ставкой и зоной «Поиск»** (``manual`` + ``search=true``).
Ответ 400 с текстом ``only for campaigns with manual bid, search placement`` —
ожидаемое поведение для всех остальных типов.

Терминология в боте (не путать с WB API)
----------------------------------------

``ComplexAdv`` всегда состоит из пары записей ``AdvSetting``:

- **auto** — ``complex_adv.adv_setting`` / ``auto_adv_id`` (тип 8 unified или
  manual без search в классификации ``connect_existing_advs._is_auto_campaign``);
- **search** — ``complex_adv.search_adv`` / аукцион (``manual`` + search).

В разговорной речи «авто» часто означает **полочную** РК (рекомендации/полка,
без поиска). В коде **auto шире полки**: сюда входят и ``unified`` (единая
ставка), и ``manual`` с ``search=false`` (с полкой или без).

Матрица ``wb_*`` после sync (см. ``tests/.../test_wb_campaign_meta.py``)
-------------------------------------------------------------------------

+------------------+--------+-----+--------------+---------------------------+
| wb_bid_type      | search | rec | shelf_only   | supports_normquery_minus  |
+==================+========+=====+==============+===========================+
| unified          | *      | *   | False        | False                     |
| manual           | True   | *   | False        | **True** (единственный OK)|
| manual           | False  | True| **True**     | False (полочная авто)     |
| manual           | False  | False| False       | False                     |
| None (нет sync)  | —      | —   | False        | False                     |
+------------------+--------+-----+--------------+---------------------------+

``wb_is_manual_shelf_only`` — узкое подмножество auto (инцидент adv_id=32824944).
``wb_supports_normquery_minus_phrases`` — единственный тип, для которого
normquery API легитимен.

Поля ``AdvSetting`` заполняются при sync кампаний из WB
(``apply_wb_campaign_meta_from_legacy_adv_data`` ← ``v2_adverts_to_legacy``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


def apply_wb_campaign_meta_from_legacy_adv_data(
    adv_setting: AdvSetting,
    adv_data: dict[str, Any],
) -> None:
    """Записать wb_* поля из legacy payload (после v2_adverts_to_legacy).

    Поля используются ``MinusPhraseManager`` и ``wb_campaign_meta`` для решения,
    вызывать ли normquery get-minus/set-minus (только manual+search) или
    пропускать полочную auto до API.

    Args:
        adv_setting: Строка AdvSetting для одной WB-кампании (adv_id).
        adv_data: ``adv.data`` из AuctionAdv/Adv; ожидаются ``bidType`` и
            ``autoParams.active`` (search/recom) из ``v2_adverts_to_legacy``.
    """
    bid_type_raw = adv_data.get("bidType")
    bid_type = str(bid_type_raw).lower() if bid_type_raw is not None else None
    auto_params = adv_data.get("autoParams") or {}
    active = auto_params.get("active") or {}
    adv_setting.wb_bid_type = bid_type
    adv_setting.wb_placement_search = bool(active.get("search"))
    adv_setting.wb_placement_recommendations = bool(active.get("recom"))


def wb_campaign_meta_known(adv: AdvSetting) -> bool:
    """True, если после sync из WB известен ``wb_bid_type``.

    Пока meta не синхронизирована, skip по типу кампании не делаем — иначе
    можно пропустить легитимный вызов для search-РК до первого sync.
    """
    return getattr(adv, "wb_bid_type", None) is not None


def wb_supports_normquery_minus_phrases(adv: AdvSetting) -> bool:
    """True, если WB normquery get-minus/set-minus применим к этой РК.

    Условие WB: ``manual`` + ``wb_placement_search is True``.

    Используется в **search-ветке** ``MinusPhraseManager``: если meta уже
    известна и условие не выполняется — не вызываем API (нет лишних 400).

    Для **auto-ветки** намеренно **не** используется как единственный критерий
    skip — см. docstring ``MinusPhraseManager._update_minuses_in_auto_adv``.
    """
    if not wb_campaign_meta_known(adv):
        return False
    return (
        getattr(adv, "wb_bid_type", None) == "manual"
        and getattr(adv, "wb_placement_search", None) is True
    )


def wb_is_manual_shelf_only(adv: AdvSetting) -> bool:
    """True для полочной auto-РК: manual, поиск выключен, рекомендации включены.

    Типичный кейс в проде: auto ``adv_id=32824944`` — manual + search=false +
    recom=true. Именно такие кампании давали 400 на normquery set-minus.

    Это **не** все auto-кампании в классификации бота (``unified`` и
    ``manual`` без search при ``rec=false`` сюда не попадают). Для них
    auto-ветка минус-фраз может всё ещё звать normquery; 400 перехватывает
    ``PromotionManager.set_minus_phrases_with_fallback`` (без падения процесса).
    Отдельная задача — unified auto через ``/adv/v1/auto/set-excluded``.
    """
    if not wb_campaign_meta_known(adv):
        return False
    return (
        getattr(adv, "wb_bid_type", None) == "manual"
        and getattr(adv, "wb_placement_search", None) is False
        and getattr(adv, "wb_placement_recommendations", None) is True
    )
