"""Unit-тесты A/B Hold allowed-set freeze + enforcement (spec card-ab-hold-mode §8).

Primary invariant: замораживается разрешённый (allowed/relevant) набор фраз;
минус — производный enforcement. Покрывает: capture allowed-set, normalize,
skip ordinary recalc, ready-only-ACTIVE, hold enforcement (новая не-разрешённая
фраза исключается / снятая разрешённая восстанавливается), WB cap видимая
деградация, wiring setup/hold/EXIT, инструкция.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.enter_status import (
    build_enter_poll_status_lines,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines import (
    process_ab_hold,
    process_ab_setup,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    card_ab_hold_status_label,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    WB_MINUS_CAP,
    capture_allowed_phrase_set,
    compute_enforced_minus,
    empty_allowed_snapshot,
    enforce_allowed_set,
    is_ab_hold_ready_for_tests,
    normalize_allowed_snapshot,
    should_skip_ordinary_minus_recalculation,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    filter_structural_act_candidates,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)

_PIPELINES = (
    "app.modules.shop_runner.service_manager.services."
    "auto_updater_v3.card_ab_hold.pipelines"
)
_SETUP_APPLY = (
    "app.modules.shop_runner.service_manager.services."
    "auto_updater_v3.card_ab_hold.setup_apply"
)


def _complex_adv(*, nmid: int = 101, auto_adv_id: int = 9) -> SimpleNamespace:
    """РК с одной auto-целью (meta unknown → не shelf-only, search=None)."""
    adv_setting = SimpleNamespace(
        nmids=[nmid],
        wb_bid_type=None,
        wb_placement_search=None,
        wb_placement_recommendations=None,
    )
    return SimpleNamespace(
        auto_adv_id=auto_adv_id,
        adv_setting=adv_setting,
        search_adv=None,
    )


async def _run_enforce(
    *,
    allowed: object,
    observed: list[str],
    current: list[str],
) -> tuple[dict[str, object], list[tuple[int, int, list[str]]]]:
    """Прогнать enforce_allowed_set для одной (9,101) цели с заданными данными."""
    calls: list[tuple[int, int, list[str]]] = []

    async def get_minus(adv_id: int, nmid: int) -> list[str]:
        _ = (adv_id, nmid)
        return list(current)

    async def get_observed(adv_id: int, nmid: int) -> list[str]:
        _ = (adv_id, nmid)
        return list(observed)

    async def set_minus(adv_id: int, nmid: int, phrases: list[str]) -> None:
        calls.append((adv_id, nmid, phrases))

    res = await enforce_allowed_set(
        _complex_adv(),
        allowed=allowed,
        get_minus=get_minus,
        set_minus=set_minus,
        get_observed=get_observed,
    )
    return dict(res), calls


@pytest.mark.unit
def test_capture_allowed_phrase_set_keeps_non_bad_texts() -> None:
    """8.1/8.5: allowed-set = тексты ключей status != BAD (BAD исключается)."""
    keywords = [
        SimpleNamespace(status=KeywordStatus.GOOD, text="good b"),
        SimpleNamespace(status=KeywordStatus.GOOD, text="good a"),
        SimpleNamespace(status=KeywordStatus.BAD, text="bad kw"),
        SimpleNamespace(status=KeywordStatus.VIEWS_IS_NOT_ENOUGH, text="warmup"),
        SimpleNamespace(status=KeywordStatus.GOOD, text=""),
    ]
    assert capture_allowed_phrase_set(keywords) == ["good a", "good b", "warmup"]


@pytest.mark.unit
def test_normalize_and_empty_allowed_snapshot() -> None:
    """8.1: normalize → sorted unique strings; empty → []."""
    assert normalize_allowed_snapshot(["b", "a", "a", "", None]) == ["a", "b"]
    assert normalize_allowed_snapshot("not-a-list") == []
    assert normalize_allowed_snapshot(None) == []
    assert empty_allowed_snapshot() == []


@pytest.mark.unit
def test_compute_enforced_minus_cap_and_diff() -> None:
    """8.6/8.7: минус = наблюдаемые вне allowed; cap отсекает + флаг."""
    minus, exceeded = compute_enforced_minus(["a", "b", "c"], ["a"])
    assert minus == ["b", "c"]
    assert exceeded is False

    observed = [f"kw{i}" for i in range(WB_MINUS_CAP + 5)]
    capped, exceeded2 = compute_enforced_minus(observed, [])
    assert len(capped) == WB_MINUS_CAP
    assert exceeded2 is True


@pytest.mark.unit
def test_ordinary_minus_recalc_skipped_on_freeze_modes() -> None:
    """8.2: PENDING/ACTIVE → ordinary allowed-set recalc skip; OFF → allowed."""
    assert should_skip_ordinary_minus_recalculation(CardAbHoldMode.PENDING_SETUP)
    assert should_skip_ordinary_minus_recalculation(CardAbHoldMode.ACTIVE)
    assert not should_skip_ordinary_minus_recalculation(CardAbHoldMode.OFF)
    pool = [
        SimpleNamespace(adv_id=1, card_ab_hold_mode="active"),
        SimpleNamespace(adv_id=2, card_ab_hold_mode="off"),
        SimpleNamespace(adv_id=3, card_ab_hold_mode="pending_setup"),
    ]
    assert [a.adv_id for a in filter_structural_act_candidates(pool)] == [2]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enforce_excludes_new_non_allowed_phrase() -> None:
    """8.2/8.6/8.10: новая не-разрешённая фраза во время hold → исключается."""
    res, calls = await _run_enforce(
        allowed=["good1", "good2"],
        observed=["good1", "new_non_allowed"],
        current=[],
    )
    assert calls == [(9, 101, ["new_non_allowed"])]
    assert res["written"] == 1
    assert res["cap_exceeded"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enforce_restores_manually_removed_allowed_phrase() -> None:
    """8.2/8.6: разрешённая фраза, заминусованная вручную → восстанавливается."""
    res, calls = await _run_enforce(
        allowed=["good1"],
        observed=["good1"],
        current=["good1"],
    )
    # good1 разрешена → её нет в целевом минусе → set_minus снимает её.
    assert calls == [(9, 101, [])]
    assert res["written"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enforce_no_write_when_surface_already_clean() -> None:
    """8.6: если минус уже равен «всё вне allowed» — без write."""
    res, calls = await _run_enforce(
        allowed=["good1"],
        observed=["good1", "bad1"],
        current=["bad1"],
    )
    assert calls == []
    assert res["written"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enforce_cap_exceeded_degrades_visibly() -> None:
    """8.7/8.10: > WB cap не-разрешённых → cap_exceeded (видимая деградация)."""
    observed = [f"kw{i}" for i in range(WB_MINUS_CAP + 10)]
    res, calls = await _run_enforce(allowed=[], observed=observed, current=[])
    assert res["cap_exceeded"] == [(9, 101)]
    assert len(calls) == 1
    _, _, phrases = calls[0]
    assert len(phrases) == WB_MINUS_CAP


@pytest.mark.unit
def test_ui_ready_for_ab_tests_only_when_active() -> None:
    """8.3: ready-to-test только ACTIVE; PENDING не ready."""
    assert is_ab_hold_ready_for_tests(CardAbHoldMode.ACTIVE) is True
    assert is_ab_hold_ready_for_tests(CardAbHoldMode.PENDING_SETUP) is False
    assert is_ab_hold_ready_for_tests(CardAbHoldMode.OFF) is False

    pending = build_enter_poll_status_lines(
        mode="pending_setup",
        abort_safe=True,
        abort_can_continue=True,
    )
    assert "можно запускать A/B" not in pending.lower()
    assert "не запускайте A/B" in pending
    assert "набор фраз ещё не зафиксирован" in pending

    active_clean = build_enter_poll_status_lines(
        mode="active",
        abort_safe=None,
        abort_can_continue=None,
        degraded=False,
    )
    assert "Можно запускать A/B-тесты" in active_clean
    assert "зафиксированы" in active_clean


@pytest.mark.unit
def test_enter_status_active_degraded_does_not_claim_clean_hold() -> None:
    """8.7/8.10 (bug fix): ACTIVE + degraded ⇒ честный статус, не «чистый» hold.

    Spec scenario «Enforcement exceeding the WB minus cap degrades visibly»:
    система MUST NOT молча заявлять чистый hold. Падал бы до фикса — параметра
    ``degraded`` не было и ACTIVE безусловно печатал «Можно запускать A/B-тесты…».
    """
    active_degraded = build_enter_poll_status_lines(
        mode="active",
        abort_safe=None,
        abort_can_continue=None,
        degraded=True,
    )
    assert "Можно запускать A/B-тесты" not in active_degraded
    assert "не гарантируется" in active_degraded


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_pipeline_orders_capture_enforce_before_active() -> None:
    """8.1/8.5: legacy ENTER path вызывает enforce до apply (не string-index).

    Epoch-managed ветка вызывает ``apply_ab_hold_setup_mutations`` раньше в
    исходнике — поэтому порядок проверяем по call-order на legacy path
    (phase IS NULL), а не через ``src.index``.
    """
    call_order: list[str] = []
    keywords = [
        SimpleNamespace(status=KeywordStatus.GOOD, text="good1"),
        SimpleNamespace(status=KeywordStatus.BAD, text="bad1"),
    ]
    complex_adv = _setup_complex_adv()
    complex_adv.get_keywords = AsyncMock(return_value=keywords)

    lock_mgr = MagicMock()
    lock_mgr.acquire = AsyncMock(return_value=True)
    lock_mgr.release = AsyncMock(return_value=None)

    async def _enforce(*_a: object, **_k: object) -> dict[str, object]:
        call_order.append("enforce")
        return {"targets": 1, "written": 0, "cap_exceeded": []}

    async def _apply(*_a: object, **_k: object) -> tuple[int, int]:
        call_order.append("apply")
        return (1, 0)

    mgr = MagicMock()
    mgr.enforce_frozen_allowed_set = AsyncMock(side_effect=_enforce)
    container = MagicMock()
    container.minus_phrase_manager.return_value = mgr

    with (
        patch(
            f"{_PIPELINES}.CardAbHoldSignalRedisCache",
            MagicMock(return_value=SimpleNamespace(client=MagicMock())),
        ),
        patch(
            f"{_PIPELINES}.CardAbHoldSetupBlockRedisCache",
            MagicMock(
                return_value=MagicMock(set_block=AsyncMock(), clear=AsyncMock())
            ),
        ),
        patch(f"{_PIPELINES}.RedisLockManager", MagicMock(return_value=lock_mgr)),
        patch(
            f"{_PIPELINES}.MinusPhraseManagerContainer",
            MagicMock(return_value=container),
        ),
        patch(
            f"{_PIPELINES}.apply_ab_hold_setup_mutations",
            AsyncMock(side_effect=_apply),
        ),
        patch(
            f"{_PIPELINES}.ensure_search_common_bid_reset_on_enter",
            new_callable=AsyncMock,
        ),
        patch(
            f"{_PIPELINES}.capture_allowed_phrase_set",
            side_effect=lambda kws: (
                call_order.append("capture")
                or [kw.text for kw in kws if kw.status != KeywordStatus.BAD]
            ),
        ),
    ):
        await process_ab_setup(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )

    assert call_order == ["capture", "enforce", "apply"]
    assert complex_adv.adv_setting.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disable_clears_allowed_snapshot() -> None:
    """8.3/8.8 EXIT clears ``card_ab_hold_allowed_phrases_snapshot`` via in_session."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
        CardAbHoldDisable,
    )

    adv = SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        wb_cabinet_id=7,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_allowed_phrases_snapshot=["good1", "good2"],
        card_ab_hold_phase=None,
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    query = MagicMock()
    query.answer = AsyncMock()
    query.message = MagicMock(answer=AsyncMock())
    query.from_user = SimpleNamespace(id=999)
    ownership = AsyncMock(return_value=SimpleNamespace(id=11))

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "get_wb_user_cabinet_for_adv_and_telegram",
            new=ownership,
        ),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
        patch.object(
            handlers,
            "CardAbHoldCommonBidEnterResetRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
        patch.object(
            handlers,
            "CardAbHoldSetupBlockRedisCache",
            return_value=MagicMock(clear=AsyncMock()),
        ),
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
        patch.object(handlers, "is_card_ab_hold_ui_visible", return_value=True),
    ):
        await handlers.disable_card_ab_hold(
            query, CardAbHoldDisable(adv_setting_original_id=42)
        )

    assert adv.card_ab_hold_mode == CardAbHoldMode.OFF.value
    assert adv.card_ab_hold_allowed_phrases_snapshot == []
    session.commit.assert_awaited()


@pytest.mark.unit
def test_instruction_mentions_allowed_set_and_scope() -> None:
    """8.9: инструкция про фиксацию набора фраз + scoped/best-effort wording."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )

    text = handlers._INSTRUCTION
    assert "набор" in text and "фраз" in text
    assert "отключите A/B Hold" in text
    assert "не гарантируется" in text


@pytest.mark.unit
def test_status_label_reflects_degradation() -> None:
    """8.7/8.10 (bug fix): ACTIVE + degraded — label не заявляет чистый «ВКЛ».

    Меню-кнопка (``card_ab_hold_status_label``) — вторая user-facing поверхность
    honest-status инварианта. Падал бы до фикса — label читал только mode.
    """
    clean = SimpleNamespace(card_ab_hold_mode="active", card_ab_hold_degraded=False)
    degraded = SimpleNamespace(card_ab_hold_mode="active", card_ab_hold_degraded=True)
    assert card_ab_hold_status_label(clean) == "A/B Hold: ВКЛ"  # type: ignore[arg-type]
    label_degraded = card_ab_hold_status_label(degraded)  # type: ignore[arg-type]
    assert label_degraded != "A/B Hold: ВКЛ"
    assert "не гарантируется" in label_degraded


# --- Write-boundary: honest degradation persisted to PG from hold tick ---


class _RecordingSession:
    """Async-сессия, записывающая исполненные statements (без реальной БД)."""

    def __init__(self, recorder: list[object]) -> None:
        self._recorder = recorder

    async def execute(self, stmt: object) -> None:
        self._recorder.append(stmt)

    async def commit(self) -> None:
        self._recorder.append("commit")

    async def __aenter__(self) -> "_RecordingSession":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False


def _fake_session_maker(recorder: list[object]):
    """Фабрика session-maker, возвращающая ``_RecordingSession`` (совместимо с ``sm``)."""

    def _sm(*_a: object, **_kw: object) -> _RecordingSession:
        return _RecordingSession(recorder)

    return _sm


def _hold_complex_adv(*, current_degraded: bool) -> SimpleNamespace:
    """ACTIVE-кампания для hold-тика; ``max_price_for_order=0`` → return после persist."""
    adv_setting = SimpleNamespace(
        id=555,
        card_ab_hold_mode="active",
        card_ab_hold_allowed_phrases_snapshot=["good1"],
        card_ab_hold_degraded=current_degraded,
        max_price_for_order=0,
    )
    return SimpleNamespace(
        adv_id=9,
        card_ab_hold_mode="active",
        adv_setting=adv_setting,
        fact_pay_for_order=None,
    )


async def _run_hold_with_enforce(
    *,
    current_degraded: bool,
    cap_exceeded: list[tuple[int, int]],
) -> tuple[list[object], SimpleNamespace]:
    """Прогнать ``process_ab_hold`` с mocked enforce и recording-сессией."""
    recorder: list[object] = []
    complex_adv = _hold_complex_adv(current_degraded=current_degraded)

    mgr = MagicMock()
    mgr.enforce_frozen_allowed_set = AsyncMock(
        return_value={"targets": 1, "written": 0, "cap_exceeded": cap_exceeded}
    )
    container = MagicMock()
    container.minus_phrase_manager.return_value = mgr

    with (
        patch(f"{_PIPELINES}.MinusPhraseManagerContainer", MagicMock(return_value=container)),
        patch(f"{_SETUP_APPLY}.sm", _fake_session_maker(recorder)),
    ):
        await process_ab_hold(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )
    return recorder, complex_adv


def _degraded_update_stmts(recorder: list[object]) -> list[object]:
    """Statements, реально пишущие card_ab_hold_degraded в PG (не 'commit')."""
    return [
        s
        for s in recorder
        if s != "commit" and "card_ab_hold_degraded" in str(s)
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hold_persists_degradation_to_pg_when_cap_exceeded() -> None:
    """8.7/8.10 (bug fix, write boundary): cap_exceeded ⇒ реальный PG update поля.

    Падал бы до фикса — тик считал cap_exceeded и логировал, но никуда не
    персистил (UI не имел durable источника честного статуса). Проверяем реальный
    ``session.execute`` с ``card_ab_hold_degraded=True``, не только return value.
    """
    recorder, complex_adv = await _run_hold_with_enforce(
        current_degraded=False,
        cap_exceeded=[(9, 101)],
    )
    stmts = _degraded_update_stmts(recorder)
    assert len(stmts) == 1
    assert stmts[0].compile().params.get("card_ab_hold_degraded") is True  # type: ignore[attr-defined]
    assert "commit" in recorder
    assert complex_adv.adv_setting.card_ab_hold_degraded is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hold_self_heals_degradation_flag_when_cap_ok() -> None:
    """8.7 (paired, self-healing): ранее degraded, cap не превышен ⇒ флаг снят в PG."""
    recorder, complex_adv = await _run_hold_with_enforce(
        current_degraded=True,
        cap_exceeded=[],
    )
    stmts = _degraded_update_stmts(recorder)
    assert len(stmts) == 1
    assert stmts[0].compile().params.get("card_ab_hold_degraded") is False  # type: ignore[attr-defined]
    assert complex_adv.adv_setting.card_ab_hold_degraded is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hold_no_pg_write_when_degradation_unchanged() -> None:
    """8.7: чистый hold и флаг уже False ⇒ без лишнего PG write (idempotent tick)."""
    recorder, complex_adv = await _run_hold_with_enforce(
        current_degraded=False,
        cap_exceeded=[],
    )
    assert _degraded_update_stmts(recorder) == []
    assert complex_adv.adv_setting.card_ab_hold_degraded is False


# --- ENTER guard: пустой allowed-set не должен давать «чистый» ACTIVE (finding #3) ---


def _setup_complex_adv() -> SimpleNamespace:
    """PENDING_SETUP-кампания для ENTER-тика ``process_ab_setup`` (spec §8).

    Spec card-ab-hold-mode «ACTIVE without ENTER setup snapshot is forbidden».
    ``adv_setting.id`` нужен для apply-вызова; ``max_price_for_order>0`` проходит
    plan_max-гейт, чтобы выполнение дошло до ветки allowed-set.
    """
    adv_setting = SimpleNamespace(
        id=555,
        adv_id=9,  # AdvSettingRedisCache key (ENTER common-bid reset)
        nmids=[101],
        max_price_for_order=100,
        card_ab_hold_mode="pending_setup",
        card_ab_hold_allowed_phrases_snapshot=None,
        card_ab_hold_degraded=False,
    )
    return SimpleNamespace(
        adv_id=9,
        shop_id=1,
        card_ab_hold_mode="pending_setup",
        adv_setting=adv_setting,
        search_adv=None,
    )


async def _run_setup_with_keywords(
    keywords: list[SimpleNamespace],
) -> tuple[AsyncMock, AsyncMock, AsyncMock, SimpleNamespace]:
    """Прогнать ``process_ab_setup`` с mocked Redis-lock / enforce / apply.

    Spec §8: проверяем, дошло ли выполнение до WB-enforce и PG-apply write boundary.
    Returns:
        (enforce_mock, apply_mock, release_mock, complex_adv).
    """
    complex_adv = _setup_complex_adv()
    complex_adv.get_keywords = AsyncMock(return_value=keywords)

    lock_mgr = MagicMock()
    lock_mgr.acquire = AsyncMock(return_value=True)
    lock_mgr.release = AsyncMock(return_value=None)

    enforce_mock = AsyncMock(
        return_value={"targets": 1, "written": 0, "cap_exceeded": []}
    )
    mgr = MagicMock()
    mgr.enforce_frozen_allowed_set = enforce_mock
    container = MagicMock()
    container.minus_phrase_manager.return_value = mgr

    apply_mock = AsyncMock(return_value=(1, 0))

    with (
        patch(
            f"{_PIPELINES}.CardAbHoldSignalRedisCache",
            MagicMock(return_value=SimpleNamespace(client=MagicMock())),
        ),
        patch(
            f"{_PIPELINES}.CardAbHoldSetupBlockRedisCache",
            MagicMock(
                return_value=MagicMock(set_block=AsyncMock(), clear=AsyncMock())
            ),
        ),
        patch(f"{_PIPELINES}.RedisLockManager", MagicMock(return_value=lock_mgr)),
        patch(
            f"{_PIPELINES}.MinusPhraseManagerContainer",
            MagicMock(return_value=container),
        ),
        patch(f"{_PIPELINES}.apply_ab_hold_setup_mutations", apply_mock),
        # Isolate setup body from §19 ENTER common-bid Redis/WB (not under test).
        patch(
            f"{_PIPELINES}.ensure_search_common_bid_reset_on_enter",
            new_callable=AsyncMock,
        ),
    ):
        await process_ab_setup(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )
    return enforce_mock, apply_mock, lock_mgr.release, complex_adv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_empty_allowed_set_aborts_before_active() -> None:
    """8.5 (bug fix, finding #3): пустой allowed-set ⇒ НЕ ACTIVE, НЕ freeze-to-zero.

    Spec «ACTIVE without ENTER setup snapshot is forbidden» / «hold enforcement does
    not treat an empty/missing allowed-set snapshot as a successful freeze». Все ключи
    BAD → ``capture_allowed_phrase_set == []``. Падал бы до фикса: enforce/apply
    вызывались и mode → ACTIVE. После фикса: ни ``enforce_frozen_allowed_set`` (WB
    freeze-to-zero), ни ``apply_ab_hold_setup_mutations`` (PG ACTIVE) не вызваны, mode
    остаётся PENDING_SETUP, snapshot не выставлен, lock снят.
    """
    keywords = [
        SimpleNamespace(status=KeywordStatus.BAD, text="bad1"),
        SimpleNamespace(status=KeywordStatus.BAD, text="bad2"),
    ]
    enforce_mock, apply_mock, release_mock, complex_adv = (
        await _run_setup_with_keywords(keywords)
    )
    enforce_mock.assert_not_called()
    apply_mock.assert_not_called()
    assert (
        complex_adv.adv_setting.card_ab_hold_mode
        == CardAbHoldMode.PENDING_SETUP.value
    )
    assert complex_adv.adv_setting.card_ab_hold_allowed_phrases_snapshot is None
    release_mock.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_non_empty_allowed_set_reaches_active() -> None:
    """8.5 (paired allowed-case): непустой allowed-set ⇒ enforce+apply+ACTIVE.

    Доказывает, что guard finding #3 блокирует ТОЛЬКО вырожденный вход, а нормальный
    ENTER по-прежнему доходит до WB-enforce и PG-apply write boundary и выставляет
    ACTIVE (без этого allowed-case ``assert_not_called`` в blocked-тесте был бы
    бессмысленным — guard мог бы «глушить» вообще всё).
    """
    keywords = [
        SimpleNamespace(status=KeywordStatus.GOOD, text="good1"),
        SimpleNamespace(status=KeywordStatus.BAD, text="bad1"),
    ]
    enforce_mock, apply_mock, release_mock, complex_adv = (
        await _run_setup_with_keywords(keywords)
    )
    enforce_mock.assert_awaited_once()
    apply_mock.assert_awaited_once()
    assert complex_adv.adv_setting.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    assert complex_adv.adv_setting.card_ab_hold_allowed_phrases_snapshot == ["good1"]
    release_mock.assert_awaited_once()
