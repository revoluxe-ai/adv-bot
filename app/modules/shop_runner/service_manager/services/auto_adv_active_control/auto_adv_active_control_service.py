"""Сервис управления активностью РК: бюджет, расписание, пауза/запуск.

Как это устроено (задумано):

- Ограничения показов по времени (расписание по часам/дням и период по датам)
  настраиваются пользователем в боте для любой кампании (кнопка «Ограничения
  показов по времени» в меню настроек РК).

- Применяются эти ограничения только здесь — в AutoAdvActiveControlService.
  Другие фоновые сервисы (бидер и т.д.) их не учитывают.

- В ensure_campaigns_active обрабатываются только кампании с включённым
  «Контролем активности кампании» (auto_budget_watchdog_enabled=True). Для них
  сервис подгружает настройки времени из БД и при «сейчас вне расписания»
  ставит РК на паузу (авто и/или поиск). Для кампаний без включённого контроля
  ограничения по времени из БД нигде не проверяются.

Итог: ограничения по времени — часть механизма «контроль активности»: пользователь
может заранее настроить расписание; оно начнёт действовать после включения
«Контроля активности кампании». Кнопка настроек времени показывается всем —
это задумано (настройка «на будущее»).
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Literal, cast
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

from app.modules import balance_manager

from app.client_bot.user_interface.handlers.time_settings.logic import (
    allowed_now_from_db_state,
)
from app.client_bot.user_interface.handlers.time_settings.repository import (
    TimeSettingsDbState,
    TimeSettingsRepository,
)
from app.core.mp.wb.api.excs import BadRequestError, StandardError
from app.core.mp.wb.api.managers import WBModifier
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    resolve_selected_cpo_contract_from_view,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    AutoReasonCode,
    AuctionReasonCode,
    CampaignActivityCommand,
    CampaignActivityReason,
    RedisCampaignActivityReasonManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from app.shared.domains.wb.utils.balance_source import (
    balance_snapshot_from_response,
    cashback_summary_from_response,
)
from app.utils.db.session_maker import get_async_session_maker as get_session_maker

logger = logging.getLogger(__name__)

MSK_TZ = timezone(timedelta(hours=3))

_time_settings_repo = TimeSettingsRepository()


def _as_finite_cost_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    return result


def _is_wb_low_budget_start_error(detail: str) -> bool:
    d = detail.lower()
    if "low budget" in d or "not enough budget" in d:
        return True
    try:
        obj = json.loads(detail)
    except (json.JSONDecodeError, TypeError):
        return False
    if isinstance(obj, dict):
        payload = cast(dict[str, Any], obj)
        err = str(payload.get("error", "")).lower()
        return "low budget" in err or "not enough budget" in err
    return False


def _text_suggests_low_budget(text: str) -> bool:
    t = text.lower()
    if "low budget" in t or "not enough budget" in t:
        return True
    if "недостат" in t and "бюдж" in t:
        return True
    return False


def _exception_text_blob(exc: BaseException) -> str:
    parts: list[str] = [str(exc), repr(exc)]
    if isinstance(exc, BadRequestError):
        parts.append(exc.detail)
    if isinstance(exc, StandardError):
        parts.append(getattr(exc, "message", ""))
        parts.append(getattr(exc, "title", ""))
    return " ".join(parts)


def _exception_chain_indicates_low_budget_on_start(exc: BaseException) -> bool:
    """True if this or __cause__/__context__ looks like WB «мало бюджета» for start/pause."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        blob = _exception_text_blob(cur)
        if _text_suggests_low_budget(blob):
            return True
        if isinstance(cur, BadRequestError) and _is_wb_low_budget_start_error(cur.detail):
            return True
        cur = cur.__cause__ or cur.__context__
    return False


@dataclass
class WbWalletOkCache:
    """Per-``ensure_campaigns_active`` run: cache WB wallet positivity per cabinet.

    ``run_tasks`` runs handlers concurrently; without coordination, many coroutines
    could miss the cache between the membership check and ``get_campaign_balance``
    (there is an ``await`` in between). Per-cabinet locks plus double-checked
    loading ensure at most one WB wallet fetch per cabinet per run.
    """

    ok_by_cabinet: dict[int, bool] = field(default_factory=dict[int, bool])
    _locks_by_cabinet: dict[int, asyncio.Lock] = field(
        default_factory=dict[int, asyncio.Lock]
    )
    _locks_meta: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def lock_for(self, wb_cabinet_id: int) -> asyncio.Lock:
        async with self._locks_meta:
            lock = self._locks_by_cabinet.get(wb_cabinet_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks_by_cabinet[wb_cabinet_id] = lock
            return lock


class AutoAdvActiveControlService:
    """Управление активностью РК: пауза/запуск по бюджету и расписанию.

    Обрабатывает только кампании с bot_active и auto_budget_watchdog_enabled.
    Для них применяет лимиты бюджета и ограничения по времени (расписание/даты).
    """

    def __init__(
        self,
        wb_modifier: WBModifier,
        tasks_manager: TasksManager,
        plan_fact_reader: PlanFactReader | None = None,
        auto_shelf_bid_control_view_provider: AutoShelfBidControlViewProvider | None = None,
        redis_campaign_activity_reason_manager: RedisCampaignActivityReasonManager | None = None,
        budget_ensure_before_start_retry: Callable[
            [ComplexAdv, Literal["auto", "search"]], Awaitable[None]
        ]
        | None = None,
        shelf_bid_control_repository: Any | None = None,
    ) -> None:
        self._wb_modifier = wb_modifier
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader or PlanFactReader()  # просят тесты, потом все это исправить, техдолг
        self._auto_shelf_bid_control_view_provider = auto_shelf_bid_control_view_provider
        self._reason_manager = redis_campaign_activity_reason_manager
        self._budget_ensure_before_start_retry = budget_ensure_before_start_retry
        # Injectable PG SoT reader for shelf-exhausted our-block (tests / wiring).
        self._shelf_bid_control_repository = shelf_bid_control_repository

    async def ensure_campaigns_active(self, advs: Iterable[ComplexAdv]) -> None:
        """Привести активность РК в соответствие с бюджетом и расписанием.

        Обрабатываются только кампании с включённым «Контролем активности»
        (auto_budget_watchdog_enabled). Для них загружаются настройки времени
        из БД; при выходе за расписание/даты РК ставится на паузу. Ограничения
        по времени нигде больше не применяются — только в этом сервисе.
        """
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
            should_suppress_budget_and_activity_restart,
        )

        # Emergency latch: ordinary schedule/budget restart Forbidden; вместо
        # этого принудительная пауза обеих ног (spec kill switch).
        latch_advs = [
            adv
            for adv in advs
            if adv.bot_active
            and should_suppress_budget_and_activity_restart(
                getattr(adv.adv_setting, "card_ab_hold_emergency_latch", False)
            )
        ]
        complex_advs = [
            adv
            for adv in advs
            if adv.bot_active
            and adv.auto_budget_watchdog_enabled  # управление активностью РК: бюджет, пополнение, расписание
            and not should_suppress_budget_and_activity_restart(
                getattr(adv.adv_setting, "card_ab_hold_emergency_latch", False)
            )
        ]
        if not complex_advs and not latch_advs:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = []

        now_msk = datetime.now(MSK_TZ)
        start_of_day = datetime.combine(now_msk.date(), time.min, tzinfo=MSK_TZ)
        end_of_day = datetime.combine(now_msk.date(), time.max, tzinfo=MSK_TZ)

        unique_adv_ids = list(
            {adv.adv_setting.id for adv in complex_advs}
            | {adv.adv_setting.id for adv in latch_advs}
        )
        # Настройки времени применяются только для этих РК (с включённым контролем)
        time_settings_by_adv: dict[int, TimeSettingsDbState | None]
        async with get_session_maker(read_only=True) as session:
            time_settings_by_adv = await _time_settings_repo.load_for_adv_ids(
                session, unique_adv_ids
            )

        wb_wallet_cache = WbWalletOkCache()
        for adv in latch_advs:
            handlers.append(
                lambda complex_adv=adv: self._emergency_latch_force_pause(complex_adv)
            )
        for adv in complex_advs:
            db_state = time_settings_by_adv[adv.adv_setting.id]
            handlers.append(
                lambda complex_adv=adv, ds=db_state, cache=wb_wallet_cache: self._auto_campaign_handler(
                    complex_adv,
                    start_of_day,
                    end_of_day,
                    db_state=ds,
                    wb_wallet_cache=cache,
                )
            )
            handlers.append(
                lambda complex_adv=adv, ds=db_state, cache=wb_wallet_cache: self._search_campaign_handler(
                    complex_adv,
                    start_of_day,
                    end_of_day,
                    db_state=ds,
                    wb_wallet_cache=cache,
                )
            )

        if not handlers:
            return None

        max_workers = self._max_workers_for(len(handlers), cap=16)
        results = await run_tasks(
            handlers,
            max_workers=max_workers,
            tasks_manager=self._tasks_manager,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Auto adv active control handler failed: %s", result
                )
        return None

    @staticmethod
    def _max_workers_for(handler_count: int, cap: int) -> int:
        return max(1, min(handler_count, cap))

    async def _emergency_latch_force_pause(self, adv: ComplexAdv) -> None:
        """Принудительная пауза Search+Auto при активном Emergency latch.

        Spec ``ab-hold-emergency-kill-switch``: latch ACTIVE → РК на паузе,
        ordinary restart Forbidden. Docstring: write-path decision carve-out.
        """
        try:
            if adv.adv_id:
                await self._wb_modifier.pause_auto_campaign(adv)
            if adv.search_adv_id:
                await self._wb_modifier.pause_auction_campaign(adv)
            logger.warning(
                "[adv_setting_id=%s] Emergency latch force-pause done",
                adv.adv_setting.id,
            )
        except Exception:
            logger.exception(
                "[adv_setting_id=%s] Emergency latch force-pause failed",
                adv.adv_setting.id,
            )

    @staticmethod
    async def _get_spend_for_adv(
        adv_id: int | None,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        if adv_id is None:
            return 0.0
        return await full_wb_adv_stat.get_spend_by_last_days(
            [adv_id],
            start_date,
            end_date,
        )

    async def _maybe_pause_for_empty_keywords_intent(
        self,
        adv: ComplexAdv,
        auto_adv_id: int,
        search_status: WBAdvActiveStatus | None,
    ) -> bool:
        """Потребить/вооружить empty-keywords intent → Search pause + reason + notify.

        Spec pause-on-empty-keywords / INC-PAUSE-02: TARGET_ENTITY_OR_LEG=SEARCH.
        ALLOWED: ``pause_auction_campaign``; FORBIDDEN: ``pause_auto_campaign``.
        Pause = следующий шаг после OFF (не concurrent с OFF).

        Двухтиковое подтверждение пустоты (Owner
        ``TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE`` / ROOT-001):
        1. Уже есть Redis intent (V3 apply после FORCE_OFF / тик-1 latch) и
           набор всё ещё пуст → consume→pause Search **только если Search
           STARTED**. Warmup ``__empty__`` не блокирует этот путь (prior
           intent = settled confirmation).
        2. No-prior-intent: активных ключей 0 и Search STARTED + **settled
           empty** (не Redis warmup ``__empty__`` / transient false-empty) →
           только ``set_intent`` (latch) и return False без consume/pause.
           Pause — на следующем ``ensure``, если intent ещё есть и пустота
           подтвердилась. ROOT-001 / tasks §7.2: warmup marker MUST NOT arm.

        Перед pause перечитывает активные ключи из ``ComplexAdv.get_keywords``.
        Если набор уже непустой (stale intent при TTL до 6h после recovery) —
        intent потребляется без WB pause / EMPTY_KEYWORDS reason / notify, и
        метод возвращает False, чтобы обычный activity-control продолжался.

        Tick2 consume при Search **не** STARTED (budget/schedule pause между
        тиками): intent потребляется, но MUST NOT ``_set_search_reason(
        EMPTY_KEYWORDS)``, MUST NOT ``notify_empty_keywords_pause`` (resume
        episode gate) и MUST NOT ``pause_auction_campaign`` — prior
        schedule/budget reason сохраняется. Return True (как skip без
        Search-ноги): activity-control не стартует Search при всё ещё
        пустых ключах.

        Returns:
            True если intent был потреблён и pause/reason/notify (или skip
            без Search / skip при Search не STARTED) выполнены; False если
            arm не нужен / только latch на тике-1 / intent отброшен как
            stale / warmup false-empty.
        """
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause import (
            EmptyKeywordsPauseIntentManager,
            count_active_keywords,
            notify_empty_keywords_pause,
            should_request_empty_keywords_pause_intent,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.decision import (
            is_warmup_false_empty_keywords,
        )

        intent_mgr = EmptyKeywordsPauseIntentManager()
        keywords = await adv.get_keywords()
        active_count = count_active_keywords(keywords)
        has_intent = await intent_mgr.peek_intent(int(auto_adv_id))

        if not has_intent:
            # Тик-1 (нет prior intent): только latch confirmation, без pause.
            # Redis ``__empty__`` warmup / Adv warmup seam → refuse (ROOT-001).
            # Search PAUSE → не ставим intent (иначе блокируется recheck-start).
            campaign_is_started = search_status == WBAdvActiveStatus.STARTED
            warmup_false_empty = await is_warmup_false_empty_keywords(
                adv=adv,
                redis_client=intent_mgr.client,
                adv_id=int(auto_adv_id),
            )
            if not should_request_empty_keywords_pause_intent(
                active_count=active_count,
                bot_active=bool(adv.bot_active),
                bot_driven_off_completed=False,
                campaign_is_started=campaign_is_started,
                is_warmup_false_empty=warmup_false_empty,
            ):
                if warmup_false_empty and active_count == 0 and campaign_is_started:
                    logger.info(
                        "Search activity: skip empty-keywords arm — Redis __empty__ "
                        "warmup / transient false-empty (not settled empty) "
                        "auto_adv_id=%s shop_id=%s active_count=%s",
                        auto_adv_id,
                        adv.shop_id,
                        active_count,
                    )
                return False
            await intent_mgr.set_intent(int(auto_adv_id))
            logger.info(
                "Search activity: empty-keywords intent latched (tick1 confirmation) "
                "without pause — await tick2 if still empty "
                "auto_adv_id=%s shop_id=%s active_count=%s",
                auto_adv_id,
                adv.shop_id,
                active_count,
            )
            # Owner two-tick: same-tick set_intent→consume→pause запрещён.
            return False

        if active_count > 0:
            # Re-validate before consume→pause: keywords may recover while intent pending.
            await intent_mgr.consume_intent(int(auto_adv_id))
            logger.info(
                "Search activity: empty-keywords intent discarded — active keywords "
                "non-empty (stale intent) auto_adv_id=%s shop_id=%s active_count=%s",
                auto_adv_id,
                adv.shop_id,
                active_count,
            )
            return False

        if not await intent_mgr.consume_intent(int(auto_adv_id)):
            return False

        search_adv_id = adv.search_adv_id
        if search_adv_id is None:
            # Нет Search-ноги: consume + skip; MUST NOT fallback на Auto pause.
            logger.info(
                "Search activity: empty-keywords intent consumed but no Search leg "
                "(skip pause, no Auto fallback) auto_adv_id=%s shop_id=%s",
                auto_adv_id,
                adv.shop_id,
            )
            return True

        if search_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Search activity: pausing auction campaign (empty keywords) "
                "search_adv_id=%s auto_adv_id=%s shop_id=%s",
                search_adv_id,
                auto_adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auction_campaign(adv)
            await self._set_search_reason(
                int(search_adv_id),
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.EMPTY_KEYWORDS,
            )
            campaign_name = str(getattr(adv.adv_setting, "name", "") or "")
            await notify_empty_keywords_pause(
                shop_id=str(adv.shop_id or ""),
                adv_id=int(auto_adv_id),
                campaign_name=campaign_name,
                intent_manager=intent_mgr,
            )
            return True

        # Search не STARTED: intent уже потреблён; не маскируем prior
        # schedule/budget reason EMPTY_KEYWORDS и не arm'им resume gate.
        logger.info(
            "Search activity: empty-keywords intent consumed but Search not "
            "STARTED (skip pause/reason/notify) search_adv_id=%s "
            "auto_adv_id=%s shop_id=%s search_status=%s",
            search_adv_id,
            auto_adv_id,
            adv.shop_id,
            search_status,
        )
        return True

    async def _drain_empty_keywords_intent_without_search(
        self,
        adv: ComplexAdv,
        auto_adv_id: int,
    ) -> None:
        """Если Search-ноги нет — потребить intent без Auto pause (no fallback)."""
        if adv.search_adv_id is not None:
            return
        await self._maybe_pause_for_empty_keywords_intent(
            adv,
            auto_adv_id,
            search_status=None,
        )

    async def _maybe_notify_empty_keywords_resume_after_search_start(
        self,
        adv: ComplexAdv,
        auto_adv_id: int,
    ) -> None:
        """Resume notify после Search start или уже-STARTED recheck.

        Spec ``User notification on empty-keywords resume/re-enable``.
        Вызывается и из PAUSE/READY → start, и из Search STARTED веток
        (common-budget / search-limit), когда keywords восстановились после
        delivered pause episode (HUNT-001).

        Gate внутри ``notify_empty_keywords_resume`` — debounce-ключ pause
        notify. Дополнительно требуем active keywords > 0, чтобы recheck
        start при пустых ключах не слал «возобновлено».
        """
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause import (
            EmptyKeywordsPauseIntentManager,
            count_active_keywords,
            notify_empty_keywords_resume,
        )

        keywords = await adv.get_keywords()
        if count_active_keywords(keywords) <= 0:
            return
        campaign_name = str(getattr(adv.adv_setting, "name", "") or "")
        await notify_empty_keywords_resume(
            shop_id=str(adv.shop_id or ""),
            adv_id=int(auto_adv_id),
            campaign_name=campaign_name,
            intent_manager=EmptyKeywordsPauseIntentManager(),
        )

    async def _set_auto_reason(
        self,
        adv_id: int,
        command: CampaignActivityCommand,
        reason_code: AutoReasonCode,
    ) -> None:
        if self._reason_manager is not None:
            await self._reason_manager.set(
                adv_id,
                "auto",
                CampaignActivityReason(command=command, reason_code=reason_code),
            )

    async def _maybe_apply_shelf_exhausted_pause(
        self,
        adv: ComplexAdv,
        *,
        auto_adv_id: int,
        auto_status: str,
    ) -> bool:
        """Если PG our-block активен — pause Auto / re-assert Redis; True = stop handler.

        Paid Telegram notify on enter when ``shelf_exhausted_notify_sent_at`` is
        None — including when Auto is already PAUSE/READY (budget/schedule/
        balance may have paused first). STARTED: pause campaign + reason + notify.
        Already not STARTED: re-assert Redis reason + notify if latch unset.
        MUST NOT pause Search. Module stays ON. Dedupe via notify_sent_at.

        Returns:
            True если our-block активен и handler должен остановиться; иначе False.
        """
        if not bool(getattr(adv.adv_setting, "auto_shelf_bid_control_enabled", False)):
            return False
        nmids: list[int] = adv.nmids
        if not nmids:
            return False
        nmid: int = nmids[0]
        from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
            AutoShelfBidControlRepository,
        )

        repo = self._shelf_bid_control_repository or AutoShelfBidControlRepository()
        state = await repo.get_state(nmid)
        if state is None or not bool(state.shelf_exhausted_pause_active):
            return False

        if auto_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto watchdog: pausing auto campaign (shelf exhausted no plan) "
                "adv_id=%s shop_id=%s nmid=%s",
                auto_adv_id,
                adv.shop_id,
                nmid,
            )
            await self._wb_modifier.pause_auto_campaign(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN,
            )
            if state.shelf_exhausted_notify_sent_at is None:
                await self._notify_shelf_exhausted_enter(
                    adv,
                    state_nmid=nmid,
                    resolve_cpo_kind=state.shelf_exhausted_resolve_cpo_kind or "max",
                    resolve_cpo_value=float(
                        state.shelf_exhausted_resolve_cpo_value or 0.0
                    ),
                    due_at=state.shelf_exhausted_due_at,
                    repository=repo,
                )
            return True

        # Already paused / ready: re-assert Redis mirror from PG SoT.
        # Enter notify must still fire when latch unset (ROOT-001).
        await self._set_auto_reason(
            auto_adv_id,
            CampaignActivityCommand.PAUSE,
            AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN,
        )
        if state.shelf_exhausted_notify_sent_at is None:
            await self._notify_shelf_exhausted_enter(
                adv,
                state_nmid=nmid,
                resolve_cpo_kind=state.shelf_exhausted_resolve_cpo_kind or "max",
                resolve_cpo_value=float(
                    state.shelf_exhausted_resolve_cpo_value or 0.0
                ),
                due_at=state.shelf_exhausted_due_at,
                repository=repo,
            )
        return True

    async def _notify_shelf_exhausted_enter(
        self,
        adv: ComplexAdv,
        *,
        state_nmid: int,
        resolve_cpo_kind: str,
        resolve_cpo_value: float,
        due_at: datetime | None,
        repository: Any | None = None,
    ) -> None:
        """Paid notify once per enter; mark PG notify_sent_at."""
        from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
            AutoShelfBidControlRepository,
        )
        from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.notify import (
            notify_shelf_exhausted_pause,
        )

        campaign_name = str(getattr(adv.adv_setting, "name", "") or "")
        shop_name = str(getattr(adv, "shop_name", None) or adv.shop_id or "")
        delivered = await notify_shelf_exhausted_pause(
            shop_id=str(adv.shop_id or ""),
            adv_id=int(adv.auto_adv_id),
            shop_name=shop_name,
            campaign_name=campaign_name,
            resolve_cpo_kind=resolve_cpo_kind,
            resolve_cpo_value=resolve_cpo_value,
            due_at=due_at,
            adv_setting_original_id=int(adv.adv_setting.id),
        )
        if delivered:
            repo = repository or self._shelf_bid_control_repository or AutoShelfBidControlRepository()
            await repo.mark_shelf_exhausted_notify_sent(
                state_nmid,
                sent_at=datetime.now(timezone.utc),
            )

    async def _maybe_open_shelf_exhausted_epoch(self, adv: ComplexAdv) -> None:
        """После реального Auto start: открыть эпоху если epoch_pending."""
        nmids: list[int] = adv.nmids
        if not nmids:
            return None
        nmid: int = nmids[0]
        from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
            AutoShelfBidControlRepository,
        )

        repo = self._shelf_bid_control_repository or AutoShelfBidControlRepository()
        state = await repo.get_state(nmid)
        if state is None or not bool(getattr(state, "shelf_exhausted_epoch_pending", False)):
            return None
        await repo.mark_shelf_exhausted_epoch_started(
            nmid,
            epoch_start=datetime.now(timezone.utc),
        )
        return None

    async def _set_search_reason(
        self,
        adv_id: int,
        command: CampaignActivityCommand,
        reason_code: AuctionReasonCode,
    ) -> None:
        if self._reason_manager is not None:
            await self._reason_manager.set(
                adv_id,
                "search",
                CampaignActivityReason(command=command, reason_code=reason_code),
            )

    async def _resolve_auto_avg_cost(
        self,
        adv: ComplexAdv,
        *,
        auto_adv_id: int,
        auto_shelf_view: AutoShelfBidControlViewDTO | None = None,
    ) -> tuple[object | None, str]:
        """Resolve selected Auto Shelf CPO first, then fall back to legacy."""
        if bool(adv.adv_setting.auto_shelf_bid_control_enabled) and (
            self._auto_shelf_bid_control_view_provider is not None
        ):
            try:
                view = auto_shelf_view
                if view is None:
                    view = await self._load_auto_shelf_view(
                        adv, auto_adv_id=auto_adv_id
                    )
                if view is not None:
                    selected_contract = resolve_selected_cpo_contract_from_view(view)
                else:
                    selected_contract = None
            except Exception:
                logger.warning(
                    "Auto watchdog: selected CPO contract failed adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                    exc_info=True,
                )
            else:
                if selected_contract is not None and selected_contract.is_available:
                    return selected_contract.selected_cpo_rub, selected_contract.source
                if selected_contract is not None:
                    logger.info(
                        "Auto watchdog: selected CPO unavailable adv_id=%s shop_id=%s reason=%s",
                        auto_adv_id,
                        adv.shop_id,
                        selected_contract.unavailable_reason,
                    )

        legacy_avg_cost = await full_wb_adv_stat.get_additional_cost_per_order_for_adv(
            auto_adv_id,
        )
        return (
            legacy_avg_cost,
            "legacy_full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        )

    async def _resolve_plan_ranked_best_cpo(
        self,
        adv: ComplexAdv,
        *,
        auto_adv_id: int,
        auto_shelf_view: AutoShelfBidControlViewDTO | None = None,
    ) -> tuple[float | None, str]:
        """Resolve authoritative shelf BEST CPO from the view provider (plan_ranked top row).

        Returns (value, source_tag) where value is float or None when missing/invalid.
        """
        if (
            self._auto_shelf_bid_control_view_provider is None
            and auto_shelf_view is None
        ):
            return None, "no_view_provider"
        try:
            view = auto_shelf_view
            if view is None:
                view = await self._load_auto_shelf_view(adv, auto_adv_id=auto_adv_id)
        except Exception:
            logger.warning(
                "Auto watchdog: build_view failed adv_id=%s shop_id=%s",
                auto_adv_id,
                adv.shop_id,
                exc_info=True,
            )
            return None, "build_view_error"
        if view is None:
            return None, "build_view_error"
        best = getattr(view, "best_cpo_bid_rub", None)
        if best is None:
            return None, "plan_ranked_missing"
        try:
            val = float(best)
        except (TypeError, ValueError):
            return None, "plan_ranked_invalid"
        if not math.isfinite(val) or val < 0:
            return None, "plan_ranked_invalid"
        return val, "plan_ranked_top"

    async def _load_auto_shelf_view(
        self,
        adv: ComplexAdv,
        *,
        auto_adv_id: int,
    ) -> AutoShelfBidControlViewDTO | None:
        """Load the auto-shelf read-only view once for the current handler pass."""
        if self._auto_shelf_bid_control_view_provider is None:
            return None
        build_view = getattr(self._auto_shelf_bid_control_view_provider, "build_view", None)
        if not callable(build_view):
            return None
        try:
            if inspect.iscoroutinefunction(build_view):
                result = await build_view(int(adv.adv_setting.id))
            else:
                result = build_view(int(adv.adv_setting.id))
            return cast(AutoShelfBidControlViewDTO | None, result)
        except Exception:
            logger.warning(
                "Auto watchdog: build_view failed adv_id=%s shop_id=%s",
                auto_adv_id,
                adv.shop_id,
                exc_info=True,
            )
            return None

    async def _start_auto_campaign_maybe_retry(self, adv: ComplexAdv) -> None:
        try:
            await self._wb_modifier.start_auto_campaign(adv)
        except Exception as exc:
            if not _exception_chain_indicates_low_budget_on_start(exc):
                raise
            if self._budget_ensure_before_start_retry is None:
                logger.warning(
                    "Auto start rejected (low budget), no retry hook: shop_id=%s auto_adv_id=%s",
                    adv.shop_id,
                    adv.auto_adv_id,
                )
                raise
            logger.info(
                "Auto start low budget from WB, ensure budget then single retry: "
                "shop_id=%s auto_adv_id=%s",
                adv.shop_id,
                adv.auto_adv_id,
            )
            await self._budget_ensure_before_start_retry(adv, "auto")
            await self._wb_modifier.start_auto_campaign(adv)

    async def _start_auction_campaign_maybe_retry(self, adv: ComplexAdv) -> None:
        try:
            await self._wb_modifier.start_auction_campaign(adv)
        except Exception as exc:
            if not _exception_chain_indicates_low_budget_on_start(exc):
                raise
            if self._budget_ensure_before_start_retry is None:
                logger.warning(
                    "Auction start rejected (low budget), no retry hook: shop_id=%s search_adv_id=%s",
                    adv.shop_id,
                    adv.search_adv_id,
                )
                raise
            logger.info(
                "Auction start low budget from WB, ensure budget then single retry: "
                "shop_id=%s search_adv_id=%s",
                adv.shop_id,
                adv.search_adv_id,
            )
            await self._budget_ensure_before_start_retry(adv, "search")
            await self._wb_modifier.start_auction_campaign(adv)

    async def _cabinet_has_positive_balance(
        self,
        adv: ComplexAdv,
        wb_wallet_cache: WbWalletOkCache,
    ) -> bool:
        wb_cabinet_id = adv.adv_setting.wb_cabinet_id
        balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
            wb_cabinet_id
        )
        total = float(balance) + float(bonus)
        if total > 0:
            return True

        cache = wb_wallet_cache.ok_by_cabinet
        if wb_cabinet_id in cache:
            return cache[wb_cabinet_id]

        lock = await wb_wallet_cache.lock_for(wb_cabinet_id)
        async with lock:
            if wb_cabinet_id in cache:
                return cache[wb_cabinet_id]

            ok_wb = False
            try:
                wb_resp = await self._wb_modifier.get_campaign_balance()
                if wb_resp:
                    snap = balance_snapshot_from_response(wb_resp)
                    cashback = cashback_summary_from_response(wb_resp)
                    wb_cashbacks_total = cashback.total
                    wb_wallet_sum = (
                        snap.balance + snap.net + snap.bonus + wb_cashbacks_total
                    )
                    ok_wb = wb_wallet_sum > 0
            except Exception:
                ok_wb = False

            cache[wb_cabinet_id] = ok_wb
            return ok_wb

    async def _auto_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
        *,
        db_state: TimeSettingsDbState | None,
        wb_wallet_cache: WbWalletOkCache,
    ) -> None:
        """Контроль Auto: budget/cost + terminal shelf-exhausted pause.

        Early-return при отсутствии ordinary cost data сохраняет запрет
        cost-rule pause, но перед ним вызывается
        ``_maybe_apply_shelf_exhausted_pause`` (модуль ON / PG our-block).
        """
        auto_adv_id = adv.auto_adv_id
        auto_status = adv.auto_adv_active_status_str
        cost_log_suffix = " (common)" if adv.use_common_budget else ""

        # Расписание/даты из настроек времени; без настроек — показы разрешены
        time_allowed = (
            allowed_now_from_db_state(db_state) if db_state else True
        )
        if not time_allowed:
            if auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (time schedule) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.TIME_SCHEDULE,
            )
            return None

        if not await self._cabinet_has_positive_balance(adv, wb_wallet_cache):
            if auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (cabinet balance <= 0) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.INSUFFICIENT_BALANCE,
            )
            return None

        # Авто-кампанию ведём только при включённом режиме продвижения полок (rec_system_mode).
        # rec_system_mode по умолчанию False — кампании без явного включения полок остаются на паузе
        # по дизайну продукта: логика контроля активности и стратегий завязана на полки (сначала
        # самые дешёвые места, затем конверсия). Это не баг, а намеренное ограничение.
        # Ранний выход только из этого обработчика; аукцион (поиск) обрабатывается отдельно
        # в _search_campaign_handler, который вызывается тем же ensure_campaigns_active.
        if not adv.rec_system_promotion_mode_active:
            if auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (rec_system mode off) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.REC_SYSTEM_MODE_OFF,
            )
            return None
        if adv.use_common_budget:
            common_limit = adv.common_budget_daily_limit or 0
            spend_auto = await self._get_spend_for_adv(
                auto_adv_id, start_of_day, end_of_day
            )
            spend_search = await self._get_spend_for_adv(
                adv.search_adv_id, start_of_day, end_of_day
            )
            combined_spend = spend_auto + spend_search
            if common_limit == 0 and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (common limit 0) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_LIMIT_0,
                )
                return None
            if common_limit == 0 and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_LIMIT_0,
                )
                return None
            if 0 < common_limit <= combined_spend and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (common spend %.2f >= limit %s) adv_id=%s shop_id=%s",
                    combined_spend,
                    common_limit,
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_SPEND_EXCEEDED,
                )
                return None
            if 0 < common_limit <= combined_spend and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_SPEND_EXCEEDED,
                )
                return None
            budget_ok = common_limit > 0 and combined_spend < common_limit
        else:
            auto_limit = adv.auto_budget_daily_limit or 0
            if auto_limit == 0 and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                await self._set_auto_reason(
                    auto_adv_id, CampaignActivityCommand.PAUSE, AutoReasonCode.AUTO_LIMIT_0
                )
                return None
            if auto_limit == 0 and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                    auto_adv_id, CampaignActivityCommand.PAUSE, AutoReasonCode.AUTO_LIMIT_0
                )
                return None
            spend_today = await self._get_spend_for_adv(
                auto_adv_id, start_of_day, end_of_day
            )
            if 0 < auto_limit <= spend_today and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign because spend %.2f >= limit %s adv_id=%s shop_id=%s",
                    spend_today,
                    auto_limit,
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.AUTO_SPEND_EXCEEDED,
                )
                return None
            if 0 < auto_limit <= spend_today and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.AUTO_SPEND_EXCEEDED,
                )
                return None
            budget_ok = auto_limit > 0 and spend_today < auto_limit

        plan = PlanFactProvider.get_plan_data(adv.adv_setting)
        plan_fact_summary = await self._plan_fact_reader.get_latest_plan_fact(
            auto_adv_id
        )
        fact_predict_orders = (
            plan_fact_summary.fact_predict_orders if plan_fact_summary else None
        )
        fact_predict_orders_value = _as_finite_cost_number(fact_predict_orders)
        if fact_predict_orders_value is None:
            logger.info(
                "Auto watchdog: insufficient cost data%s adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            # ROOT-001 / INC-AUTO-SHELF-PAUSE-01: missing ordinary cost data must
            # not skip terminal shelf-exhausted pause (PG our-block). Ordinary
            # cost-rule pause remains blocked by this early-return.
            await self._maybe_apply_shelf_exhausted_pause(
                adv, auto_adv_id=auto_adv_id, auto_status=auto_status
            )
            return None
        target_cost = resolve_target_cost(
            plan.orders if plan else None,
            plan.target_pay_for_order if plan else None,
            plan.max_pay_for_order if plan else None,
            fact_predict_orders_value,
        )
        auto_shelf_view: AutoShelfBidControlViewDTO | None = None
        if bool(adv.adv_setting.auto_shelf_bid_control_enabled) and (
            self._auto_shelf_bid_control_view_provider is not None
        ):
            auto_shelf_view = await self._load_auto_shelf_view(
                adv, auto_adv_id=auto_adv_id
            )
        avg_cost, _avg_cost_source = await self._resolve_auto_avg_cost(
            adv,
            auto_adv_id=auto_adv_id,
            auto_shelf_view=auto_shelf_view,
        )
        fact_pay_for_order = (
            plan_fact_summary.fact_pay_for_order if plan_fact_summary else None
        )
        target_cost_value = _as_finite_cost_number(target_cost)
        avg_cost_value = _as_finite_cost_number(avg_cost)

        # When target cost is missing or not comparable, do not pause by cost-rule.
        # Also do not record PAUSE here, because WB state may still be running.
        # Terminal shelf-exhausted pause still runs (same invariant as above).
        if target_cost_value is None:
            logger.info(
                "Auto watchdog: insufficient cost data%s adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            await self._maybe_apply_shelf_exhausted_pause(
                adv, auto_adv_id=auto_adv_id, auto_status=auto_status
            )
            return None
        fact_pay_for_order_value = _as_finite_cost_number(fact_pay_for_order)

        # New behavior: for auto_shelf-enabled campaigns, prefer authoritative
        # BEST CPO from the view provider (plan_ranked top) for pause decision.
        # Do not use legacy avg as a substitute. If best CPO missing/invalid,
        # apply degraded rule based only on fact_pay_for_order.
        cost_rule_failed: bool
        cpo_source: str = "avg_cost_legacy"
        best_cpo_value: float | None = None
        if bool(adv.adv_setting.auto_shelf_bid_control_enabled) and (
            self._auto_shelf_bid_control_view_provider is not None
        ):
            best_cpo_value, cpo_source = await self._resolve_plan_ranked_best_cpo(
                adv,
                auto_adv_id=auto_adv_id,
                auto_shelf_view=auto_shelf_view,
            )
            if best_cpo_value is not None:
                cost_rule_failed = (
                    best_cpo_value > target_cost_value
                    and fact_pay_for_order_value is not None
                    and fact_pay_for_order_value > target_cost_value
                )
            else:
                # degraded (missing/invalid best CPO, build_view error, no
                # provider, or no callable build_view): do not block start/stop
                # by cost rule, because there is no authoritative bidder input.
                cost_rule_failed = False
        else:
            # legacy behavior: avg_cost_value (selected or legacy) drives pause
            if avg_cost_value is None:
                logger.info(
                    "Auto watchdog: insufficient cost data%s adv_id=%s shop_id=%s",
                    cost_log_suffix,
                    auto_adv_id,
                    adv.shop_id,
                )
                return None
            cost_rule_failed = (
                avg_cost_value > target_cost_value
                and fact_pay_for_order_value is not None
                and fact_pay_for_order_value > target_cost_value
            )
        logger.debug(
            "auto_watchdog_cost_decision adv_id=%s cpo_source=%s best_cpo=%s avg_cpo=%s fact_cpo=%s target=%s",
            auto_adv_id,
            cpo_source,
            best_cpo_value,
            avg_cost_value,
            fact_pay_for_order_value,
            target_cost_value,
        )
        cost_value_for_log = (
            best_cpo_value
            if best_cpo_value is not None
            else avg_cost_value
            if avg_cost_value is not None
            else fact_pay_for_order_value
        )
        if cost_rule_failed and auto_status == WBAdvActiveStatus.STARTED:
            if bool(adv.adv_setting.auto_shelf_bid_control_enabled):
                # INC-AUTO-SHELF-PAUSE-01: mid-cycle ordinary cost pause Forbidden
                # while shelf module ON (terminal path owns Auto pause).
                logger.info(
                    "Auto watchdog: skip mid-cycle cost pause (shelf module on)%s "
                    "adv_id=%s shop_id=%s best_cpo=%s fact_cpo=%s target=%s",
                    cost_log_suffix,
                    auto_adv_id,
                    adv.shop_id,
                    best_cpo_value,
                    fact_pay_for_order_value,
                    target_cost_value,
                )
            else:
                logger.info(
                    "Auto watchdog: pausing auto campaign%s due to high cost "
                    "%.2f and total CPO %.2f vs target %.2f adv_id=%s shop_id=%s",
                    cost_log_suffix,
                    cost_value_for_log,
                    fact_pay_for_order_value,
                    target_cost_value,
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COST_RULE_FAILED,
                )
                return None
        if (
            cost_rule_failed
            and auto_status != WBAdvActiveStatus.STARTED
            and not bool(adv.adv_setting.auto_shelf_bid_control_enabled)
        ):
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.COST_RULE_FAILED,
            )
            return None

        # Determine cost_rule_ok (used for resume/start) using same authoritative
        # source as pause decision to avoid resume mismatches.
        if bool(adv.adv_setting.auto_shelf_bid_control_enabled):
            # Shelf ON: ordinary cost is not a start blocker; terminal our-block
            # and other priority reasons gate start instead.
            cost_rule_ok = True
        else:
            # avg_cost_value is guaranteed non-None here: the legacy pause-decision
            # branch above returns early when it is None.
            assert avg_cost_value is not None
            cost_rule_ok = avg_cost_value <= target_cost_value

        # INC-AUTO-SHELF-PAUSE-01: execute / re-assert terminal shelf-exhausted.
        shelf_block = await self._maybe_apply_shelf_exhausted_pause(
            adv, auto_adv_id=auto_adv_id, auto_status=auto_status
        )
        if shelf_block:
            return None

        # INC-PAUSE-02: empty-keywords pause исполняет Search handler.
        # Без Search-ноги — drain intent здесь (no Auto fallback), Auto идёт дальше.
        await self._drain_empty_keywords_intent_without_search(adv, auto_adv_id)

        if (
            budget_ok
            and cost_rule_ok
            and auto_status in [WBAdvActiveStatus.PAUSE, WBAdvActiveStatus.READY_FOR_START]
        ):
            logger.info(
                "Auto budget watcher: starting auto campaign%s adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            await self._start_auto_campaign_maybe_retry(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.STARTED,
                AutoReasonCode.BUDGET_OK_COST_OK,
            )
            await self._maybe_open_shelf_exhausted_epoch(adv)
        elif budget_ok and cost_rule_ok and auto_status == WBAdvActiveStatus.STARTED:
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.STARTED,
                AutoReasonCode.BUDGET_OK_COST_OK,
            )

    async def _search_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
        *,
        db_state: TimeSettingsDbState | None,
        wb_wallet_cache: WbWalletOkCache,
    ) -> None:
        adv_id = adv.search_adv_id
        if adv_id is None:
            return None

        search_status = adv.search_adv_active_status_str

        # Расписание/даты из настроек времени; без настроек — показы разрешены
        time_allowed = (
            allowed_now_from_db_state(db_state) if db_state else True
        )
        if not time_allowed:
            if search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (time schedule) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.TIME_SCHEDULE,
            )
            return None

        if not await self._cabinet_has_positive_balance(adv, wb_wallet_cache):
            if search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (cabinet balance <= 0) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.INSUFFICIENT_BALANCE,
            )
            return None

        if adv.use_common_budget:
            common_limit = adv.common_budget_daily_limit or 0
            spend_auto = await self._get_spend_for_adv(
                adv.auto_adv_id, start_of_day, end_of_day
            )
            spend_search = await self._get_spend_for_adv(
                adv_id, start_of_day, end_of_day
            )
            combined_spend = spend_auto + spend_search
            if common_limit == 0 and search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (common limit 0) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_LIMIT_0,
                )
                return None
            if common_limit == 0 and search_status != WBAdvActiveStatus.STARTED:
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_LIMIT_0,
                )
                return None
            if 0 < common_limit <= combined_spend and search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (common spend %.2f >= limit %s) adv_id=%s shop_id=%s",
                    combined_spend,
                    common_limit,
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_SPEND_EXCEEDED,
                )
                return None
            if 0 < common_limit <= combined_spend and search_status != WBAdvActiveStatus.STARTED:
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_SPEND_EXCEEDED,
                )
                return None
            # Spec pause-on-empty-keywords: Search pause после schedule/budget gates.
            auto_adv_id = adv.auto_adv_id
            if await self._maybe_pause_for_empty_keywords_intent(
                adv,
                int(auto_adv_id),
                search_status,
            ):
                return None
            if common_limit > 0 and combined_spend < common_limit and search_status in [
                WBAdvActiveStatus.PAUSE,
                WBAdvActiveStatus.READY_FOR_START,
            ]:
                logger.info(
                    "Auto budget watcher: starting auction campaign (common) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._start_auction_campaign_maybe_retry(adv)
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.STARTED,
                    AuctionReasonCode.COMMON_OK,
                )
                await self._maybe_notify_empty_keywords_resume_after_search_start(
                    adv,
                    int(auto_adv_id),
                )
            elif (
                common_limit > 0
                and combined_spend < common_limit
                and search_status == WBAdvActiveStatus.STARTED
            ):
                # HUNT-001: Search уже STARTED; keywords могли восстановиться
                # после delivered pause — resume notify на том же helper, что
                # и при PAUSE/READY → start.
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.STARTED,
                    AuctionReasonCode.COMMON_OK,
                )
                await self._maybe_notify_empty_keywords_resume_after_search_start(
                    adv,
                    int(auto_adv_id),
                )
            return None

        spend_today = await self._get_spend_for_adv(adv_id, start_of_day, end_of_day)
        search_limit = adv.search_auto_budget_daily_limit or 0

        if 0 < search_limit <= spend_today:
            if search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign because spend %.2f >= limit %s adv_id=%s shop_id=%s",
                    spend_today,
                    search_limit,
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.SEARCH_SPEND_EXCEEDED,
            )
            return

        # Spec pause-on-empty-keywords / INC-PAUSE-02: Search pause после budget gates.
        auto_adv_id = adv.auto_adv_id
        if await self._maybe_pause_for_empty_keywords_intent(
            adv,
            int(auto_adv_id),
            search_status,
        ):
            return None

        if search_limit > 0 and search_status in [WBAdvActiveStatus.PAUSE, WBAdvActiveStatus.READY_FOR_START]:
            logger.info(
                "Auto budget watcher: starting auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._start_auction_campaign_maybe_retry(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.STARTED,
                AuctionReasonCode.SEARCH_LIMIT_OK,
            )
            await self._maybe_notify_empty_keywords_resume_after_search_start(
                adv,
                int(auto_adv_id),
            )
        elif search_limit > 0 and search_status == WBAdvActiveStatus.STARTED:
            # HUNT-001: Search уже STARTED; keywords могли восстановиться
            # после delivered pause — resume notify на том же helper, что
            # и при PAUSE/READY → start.
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.STARTED,
                AuctionReasonCode.SEARCH_LIMIT_OK,
            )
            await self._maybe_notify_empty_keywords_resume_after_search_start(
                adv,
                int(auto_adv_id),
            )
        elif search_limit == 0 and search_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto budget watcher: pausing auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auction_campaign(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.SEARCH_LIMIT_0,
            )
        elif search_limit == 0 and search_status != WBAdvActiveStatus.STARTED:
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.SEARCH_LIMIT_0,
            )
