"""FINDING-PBH-001 RED: epoch S1 keyword candidates empty after enable.

После epoch-managed Enable (``start_epoch_on_enable`` → ``AWAITING_KEYWORD_CONFIRM``)
S1 читает кандидатов только из ``card_ab_hold_allowed_phrases_snapshot`` /
``card_ab_hold_confirmed_keywords_json``. Enable не материализует snapshot;
``process_ab_setup`` (capture allowed-set) пропускается для epoch-managed.
Итог: пустой S1 → confirm «Выберите хотя бы один ключ».

До фикса тест обязан падать: ``_keyword_candidates`` / S1 render пусты, хотя
eligibility source (CalculatedKeyword + setup classifier PFO/≥100 views) имеет
PASS-ключи. После фикса — non-empty candidates на той же поверхности.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AB_HOLD_S1_SOURCE_KEYWORDS_ATTR,
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahKeywordSetConfirm,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
    selected_keywords,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_screens import (
    build_s1_text,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)

_EMPTY_CANDIDATES_TOAST = "Выберите хотя бы один ключ"


def _make_fsm() -> FSMContext:
    """Минимальный FSM для confirm-flow unit-тестов."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    return FSMContext(storage=storage, key=key)


def _make_query() -> MagicMock:
    """CallbackQuery со Message.edit_text / message.answer (не CallbackQuery.answer)."""
    msg = MagicMock(spec=Message)
    msg.edit_text = AsyncMock()
    msg.answer = AsyncMock()
    query = MagicMock()
    query.message = msg
    query.answer = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
    return query


def _calc_kw(
    *,
    text: str,
    views: int,
    pfo: float | None,
    status: KeywordStatus = KeywordStatus.GOOD,
) -> SimpleNamespace:
    """CalculatedKeyword-подобный объект eligibility read-model."""
    return SimpleNamespace(
        text=text,
        views=views,
        pay_for_order=pfo,
        status=status,
    )


def _eligible_s1_texts(
    keywords: list[SimpleNamespace],
    *,
    max_pay_for_order: float,
) -> list[str]:
    """Тексты ключей, прошедших S1 eligibility (UX copy / setup classifier).

    S1 утверждает: pay_for_order ≤ план max CPO и ≥100 показов — тот же критерий,
    что ``classify_ab_hold_setup_keyword`` PASS.
    """
    out: list[str] = []
    for kw in keywords:
        if getattr(kw, "status", None) == KeywordStatus.BAD:
            continue
        action = classify_ab_hold_setup_keyword(
            pay_for_order=kw.pay_for_order,
            views=int(kw.views),
            max_pay_for_order=max_pay_for_order,
        )
        if action == AbHoldSetupAction.PASS_FIX_TARGET:
            text = str(kw.text or "")
            if text:
                out.append(text)
    return out


def _post_epoch_enable_adv(*, max_pay_for_order: float = 100.0) -> SimpleNamespace:
    """Состояние AdvSetting сразу после epoch-managed Enable.

    phase = AWAITING_KEYWORD_CONFIRM; snapshot и confirmed JSON пусты —
    ``start_epoch_on_enable`` пишет только mode/phase; legacy setup skipped.
    """
    return SimpleNamespace(
        id=901,
        adv_id=9901,
        bot_active=True,
        max_price_for_order=max_pay_for_order,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value,
        card_ab_hold_allowed_phrases_snapshot=None,
        card_ab_hold_confirmed_keywords_json=None,
        card_ab_hold_generation=0,
        card_ab_hold_warmup_started_at=None,
        card_ab_hold_warmup_duration_hours=None,
        card_ab_hold_degraded=False,
    )


def _eligibility_source(*, max_pay_for_order: float = 100.0) -> list[SimpleNamespace]:
    """Read-model с PASS и FAIL ключами (sanity: eligibility не пуст)."""
    _ = max_pay_for_order
    return [
        _calc_kw(text="eligible-alpha", views=150, pfo=80.0),
        _calc_kw(text="eligible-beta", views=100, pfo=100.0),
        _calc_kw(text="fail-low-views", views=50, pfo=40.0),
        _calc_kw(text="fail-over-pfo", views=200, pfo=120.0),
        _calc_kw(text="fail-bad", views=300, pfo=10.0, status=KeywordStatus.BAD),
    ]


def _attach_eligibility_source(adv: SimpleNamespace, source: list[SimpleNamespace]) -> None:
    """NON_WEAKEN fixture: inject CalculatedKeyword source the live loader uses.

    Production ``_resolve_keyword_candidates`` loads via keyboard read-model and
    caches on ``AB_HOLD_S1_SOURCE_KEYWORDS_ATTR``; unit tests attach the same
    surface without PG/CH. Snapshot/confirmed remain empty (bug preconditions).
    """
    setattr(adv, AB_HOLD_S1_SOURCE_KEYWORDS_ATTR, list(source))


@pytest.mark.unit
def test_epoch_s1_keyword_candidates_nonempty_when_eligible_exist_after_enable() -> None:
    """FINDING-PBH-001: S1 ``_keyword_candidates`` MUST be non-empty after enable.

    Scenario: epoch enable completed; snapshot/confirmed empty; eligibility
    source has PASS keys. Contract: S1 read surface returns those keys.
    Fails on current code (candidates == []).
    """
    max_pfo = 100.0
    source = _eligibility_source(max_pay_for_order=max_pfo)
    expected = _eligible_s1_texts(source, max_pay_for_order=max_pfo)
    assert expected == ["eligible-alpha", "eligible-beta"], (
        "test fixture broken: eligibility source must yield PASS keys"
    )

    adv = _post_epoch_enable_adv(max_pay_for_order=max_pfo)
    assert adv.card_ab_hold_phase == CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value
    assert not (adv.card_ab_hold_allowed_phrases_snapshot or [])
    assert not (adv.card_ab_hold_confirmed_keywords_json or [])

    # Live eligible read-model feeds `_keyword_candidates` while snapshot empty.
    _attach_eligibility_source(adv, source)
    candidates = confirm_handlers._keyword_candidates(adv)

    assert candidates, (
        "FINDING-PBH-001: S1 `_keyword_candidates` empty after epoch-managed "
        "enable despite eligible keywords %r "
        "(snapshot/confirmed unset; process_ab_setup skipped for epoch). "
        "Confirm would alert «%s»." % (expected, _EMPTY_CANDIDATES_TOAST)
    )
    assert set(expected).issubset(set(candidates)), (
        "S1 candidates %r must include eligibility PASS set %r"
        % (candidates, expected)
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_epoch_s1_render_lists_eligible_keywords_after_enable() -> None:
    """FINDING-PBH-001: ``_render_for_adv`` S1 MUST list eligible keys after enable.

    Same empty-snapshot post-enable adv; render path uses ``_keyword_candidates``.
    Fails while candidates stay empty (S1 body without keyword rows).
    """
    max_pfo = 100.0
    source = _eligibility_source(max_pay_for_order=max_pfo)
    expected = _eligible_s1_texts(source, max_pay_for_order=max_pfo)
    assert expected

    adv = _post_epoch_enable_adv(max_pay_for_order=max_pfo)
    state = _make_fsm()
    query = _make_query()

    with (
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch(
            "app.client_bot.utils.get_keywords_for_keyboard",
            new=AsyncMock(return_value=source),
        ),
    ):
        await confirm_handlers._render_for_adv(query, adv, state)

    edit_args = query.message.edit_text.await_args
    assert edit_args is not None, "S1 render must edit the confirm message"
    text = edit_args.args[0] if edit_args.args else edit_args.kwargs.get("text", "")
    assert "Подтверждение набора ключей" in text

    missing = [kw for kw in expected if kw not in text]
    assert not missing, (
        "FINDING-PBH-001: S1 render after epoch enable missing eligible "
        "keywords %r (text has no candidate rows; `_keyword_candidates` empty). "
        "excerpt=%r" % (missing, text[:240])
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_epoch_s1_confirm_not_dead_end_when_eligible_exist_after_enable() -> None:
    """FINDING-PBH-001: keyword-set confirm MUST NOT toast empty-set when eligibility exists.

    Default draft includes all candidates; with empty ``_keyword_candidates``
    ``selected_keywords`` is [] → «Выберите хотя бы один ключ». After fix,
    candidates nonempty → confirm proceeds (warmup write mocked).
    """
    max_pfo = 100.0
    source = _eligibility_source(max_pay_for_order=max_pfo)
    expected = _eligible_s1_texts(source, max_pay_for_order=max_pfo)
    assert expected

    adv = _post_epoch_enable_adv(max_pay_for_order=max_pfo)
    state = _make_fsm()
    query = _make_query()
    callback = CahKeywordSetConfirm(
        adv_setting_original_id=int(adv.id),
        step=ConfirmStep.S1.value,
        revision=1,
    )

    # Sanity: without live source, snapshot/confirmed empty ⇒ still no candidates
    # (precondition of FINDING-PBH-001). Loader injects eligibility below.
    assert selected_keywords(confirm_handlers._keyword_candidates(adv), {}) == []

    with (
        patch.object(confirm_handlers, "_load_adv", new=AsyncMock(return_value=adv)),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.client_bot.utils.get_keywords_for_keyboard",
            new=AsyncMock(return_value=source),
        ),
        patch.object(
            confirm_handlers,
            "confirm_keyword_set_and_start_warmup",
            new=AsyncMock(),
        ) as mock_confirm,
        patch.object(
            confirm_handlers,
            "_render_for_adv",
            new=AsyncMock(),
        ),
    ):
        await confirm_handlers.on_keyword_set_confirm(query, callback, state)

    query.answer.assert_not_awaited()
    answer_args = query.message.answer.await_args
    assert answer_args is not None
    answer_text = answer_args.args[0] if answer_args.args else ""

    assert answer_text != _EMPTY_CANDIDATES_TOAST, (
        "FINDING-PBH-001: on_keyword_set_confirm dead-ends with «%s» after "
        "epoch enable even though eligibility source has %r — S1 candidates "
        "were empty." % (_EMPTY_CANDIDATES_TOAST, expected)
    )
    assert "подтвержд" in answer_text.lower()
    mock_confirm.assert_awaited()
    confirmed_keywords = mock_confirm.await_args.args[1]
    assert set(expected).issubset(set(confirmed_keywords))


@pytest.mark.unit
def test_s1_text_contract_claims_eligibility_list_when_candidates_provided() -> None:
    """Allowed sibling: ``build_s1_text`` lists provided candidates (UX surface OK)."""
    text = build_s1_text(
        keywords=["eligible-alpha"],
        page=0,
        total_pages=1,
        draft={},
        is_s1b=False,
    )
    assert "eligible-alpha" in text
    assert "≥100 показов" in text or "100 показов" in text
