"""ContractCase для ``notify_empty_keywords_pause`` (scenario stub ↔ boundary).

Spec pause-on-empty-keywords: activity-control вызывает notify keyword-only
после Search pause. Shared cases — единый source для scenario_seam AsyncMock
и boundary tests, которые зовут реальный ``notify_empty_keywords_pause``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

CONTRACT_ID = "empty-keywords-notify-v1"

# Keyword-only args, которые production всегда передаёт из activity-control.
NOTIFY_REQUIRED_KWONLY: frozenset[str] = frozenset(
    {"shop_id", "adv_id", "campaign_name"}
)


@dataclass(frozen=True)
class NotifyEmptyKeywordsContractCase:
    """Ожидаемые kwargs thin-end notify после empty-keywords Search pause."""

    case_id: str
    shop_id: str
    adv_id: int
    campaign_name: str

    def as_required_kwargs(self) -> dict[str, Any]:
        """Минимальный production call shape (без optional injectables)."""
        return {
            "shop_id": self.shop_id,
            "adv_id": self.adv_id,
            "campaign_name": self.campaign_name,
        }


# Scenario FakeComplexAdv defaults (shop-empty-kw / 9001 / Тестовая РК).
NOTIFY_AFTER_SEARCH_PAUSE_CASE = NotifyEmptyKeywordsContractCase(
    case_id="notify_after_search_pause_activity",
    shop_id="shop-empty-kw",
    adv_id=9001,
    campaign_name="Тестовая РК",
)

# Boundary telegram / message path vectors.
NOTIFY_TELEGRAM_BOUNDARY_CASE = NotifyEmptyKeywordsContractCase(
    case_id="notify_telegram_boundary",
    shop_id="shop-tg-1",
    adv_id=9001,
    campaign_name="РК Empty",
)

# Boundary PG PURE_READ handoff vector.
NOTIFY_PG_HANDOFF_CASE = NotifyEmptyKeywordsContractCase(
    case_id="notify_pg_handoff_boundary",
    shop_id="shop-pg-1",
    adv_id=9001,
    campaign_name="Test",
)

NOTIFY_CONTRACT_CASES: tuple[NotifyEmptyKeywordsContractCase, ...] = (
    NOTIFY_AFTER_SEARCH_PAUSE_CASE,
    NOTIFY_TELEGRAM_BOUNDARY_CASE,
    NOTIFY_PG_HANDOFF_CASE,
)


def assert_notify_kwargs_match_case(
    kwargs: Mapping[str, Any],
    case: NotifyEmptyKeywordsContractCase,
    *,
    require_intent_manager: bool = False,
) -> None:
    """Executable parity: required kwonly keys + values == ContractCase."""
    missing = NOTIFY_REQUIRED_KWONLY - set(kwargs)
    assert not missing, f"notify kwargs missing {sorted(missing)} for {case.case_id}"
    assert kwargs["shop_id"] == case.shop_id
    assert kwargs["adv_id"] == case.adv_id
    assert kwargs["campaign_name"] == case.campaign_name
    if require_intent_manager:
        assert "intent_manager" in kwargs
        assert kwargs["intent_manager"] is not None


def assert_notify_mock_matches_case(
    notify_mock: Any,
    case: NotifyEmptyKeywordsContractCase,
    *,
    require_intent_manager: bool = True,
) -> None:
    """Scenario stub: AsyncMock awaited once with ContractCase kwargs."""
    notify_mock.assert_awaited_once()
    call = notify_mock.await_args
    assert call is not None
    assert call.args == (), "notify_empty_keywords_pause is keyword-only"
    assert_notify_kwargs_match_case(
        call.kwargs,
        case,
        require_intent_manager=require_intent_manager,
    )
