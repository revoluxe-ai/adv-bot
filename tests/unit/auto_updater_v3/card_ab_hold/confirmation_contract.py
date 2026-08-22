"""Общие executable ContractCases для границ подтверждения A/B Hold.

Модуль является единым источником входов и ожидаемых observable-результатов
для scenario-seam тестов, Telegram/factual stub-contract тестов и provider
boundary тестов. Production DTO не дублируются: factual loader получает
production-shaped объекты ``text`` + ``cluster_stat.position``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf, nan
from types import SimpleNamespace
from typing import Final


@dataclass(frozen=True)
class FactualPositionContractCase:
    """Описать один W3 factual-input vector и его валидируемый результат."""

    case_id: str
    positions: dict[str, object]
    expected_rows: tuple[tuple[str, int, int], ...]
    expected_exclusions: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class OwnerContractCase:
    """Описать associated/foreign actor outcome на callback boundary."""

    case_id: str
    associated: bool
    expected_neutral_notice: bool


@dataclass(frozen=True)
class WbSyncContractCase:
    """Описать request/response/failure shape тонкого WB sync конца."""

    case_id: str
    keywords: tuple[str, ...]
    expected_allowed_snapshot: tuple[str, ...]
    enforce_response: dict[str, bool]
    failure_message: str


@dataclass(frozen=True)
class EpochDriftContractCase:
    """Описать read-only factual drift при неизменном durable target."""

    case_id: str
    factual_position: float
    confirmed_target_place: int


@dataclass(frozen=True)
class LifecycleContractCase:
    """Описать shared transport/effect expectations полного confirmation flow."""

    case_id: str
    retry_case_id: str
    redis_enter_events: tuple[str, ...]
    minimum_telegram_notifications: int
    wb_sync_calls: int


CONTRACT_ID: Final[str] = "cah.confirmation-boundaries.v1"

CAH_OWN_ASSOCIATED_001: Final[OwnerContractCase] = OwnerContractCase(
    case_id="CAH-OWN-ASSOCIATED-001",
    associated=True,
    expected_neutral_notice=False,
)
CAH_OWN_FOREIGN_CONFIRM_001: Final[OwnerContractCase] = OwnerContractCase(
    case_id="CAH-OWN-FOREIGN-CONFIRM-001",
    associated=False,
    expected_neutral_notice=True,
)
CAH_OWN_FOREIGN_DISABLE_001: Final[OwnerContractCase] = OwnerContractCase(
    case_id="CAH-OWN-FOREIGN-DISABLE-001",
    associated=False,
    expected_neutral_notice=True,
)
CAH_OWN_UNRELATED_WRITERS_001: Final[OwnerContractCase] = OwnerContractCase(
    case_id="CAH-OWN-UNRELATED-WRITERS-001",
    associated=True,
    expected_neutral_notice=False,
)

CAH_TP_POSITIVE_001: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-POSITIVE-001",
        positions={"alpha": 12.0},
        expected_rows=(("alpha", 12, 12),),
        expected_exclusions=(),
    )
)
CAH_TP_FIELD_SEPARATION_001: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-FIELD-SEPARATION-001",
        positions={"alpha": 12.0},
        expected_rows=(("alpha", 12, 12),),
        expected_exclusions=(),
    )
)
CAH_TP_MISSING_001: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-MISSING-001",
        positions={},
        expected_rows=(),
        expected_exclusions=(("alpha", "фактическая позиция недоступна"),),
    )
)
CAH_TP_ZERO_001: Final[FactualPositionContractCase] = FactualPositionContractCase(
    case_id="CAH-TP-ZERO-001",
    positions={"alpha": 0.0},
    expected_rows=(),
    expected_exclusions=(("alpha", "фактическая позиция неположительная"),),
)
CAH_TP_NEGATIVE_001: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-NEGATIVE-001",
        positions={"alpha": -1.0},
        expected_rows=(),
        expected_exclusions=(("alpha", "фактическая позиция неположительная"),),
    )
)
CAH_TP_NONFINITE_001: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-NONFINITE-001",
        positions={"alpha": nan},
        expected_rows=(),
        expected_exclusions=(("alpha", "фактическая позиция недоступна"),),
    )
)
CAH_TP_MIXED_001: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-MIXED-001",
        positions={"alpha": 14.0, "beta": 0.0},
        expected_rows=(("alpha", 14, 14),),
        expected_exclusions=(("beta", "фактическая позиция неположительная"),),
    )
)
CAH_TP_EMPTY_001: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-EMPTY-001",
        positions={"alpha": -1.0, "beta": inf},
        expected_rows=(),
        expected_exclusions=(
            ("alpha", "фактическая позиция неположительная"),
            ("beta", "фактическая позиция недоступна"),
        ),
    )
)
CAH_TP_FIELD_SEPARATION_002: Final[FactualPositionContractCase] = (
    FactualPositionContractCase(
        case_id="CAH-TP-FIELD-SEPARATION-002",
        positions={"alpha": 12.0},
        expected_rows=(("alpha", 12, 12),),
        expected_exclusions=(),
    )
)

FACTUAL_POSITION_CASES: Final[
    tuple[FactualPositionContractCase, ...]
] = (
    CAH_TP_POSITIVE_001,
    CAH_TP_FIELD_SEPARATION_001,
    CAH_TP_MISSING_001,
    CAH_TP_ZERO_001,
    CAH_TP_NEGATIVE_001,
    CAH_TP_NONFINITE_001,
    CAH_TP_MIXED_001,
    CAH_TP_EMPTY_001,
    CAH_TP_FIELD_SEPARATION_002,
)


def production_factual_rows(
    case: FactualPositionContractCase,
) -> list[SimpleNamespace]:
    """Построить production-shaped rows для keyboard factual loader.

    Args:
        case: Общий factual ContractCase с raw ``cluster_stat.position``.

    Returns:
        Список объектов с теми полями, которые читает production loader.
    """
    return [
        SimpleNamespace(
            text=keyword,
            cluster_stat=SimpleNamespace(position=position),
        )
        for keyword, position in case.positions.items()
    ]


CAH_EPOCH_RETRY_001: Final[WbSyncContractCase] = WbSyncContractCase(
    case_id="CAH-EPOCH-RETRY-001",
    keywords=("alpha",),
    expected_allowed_snapshot=("alpha",),
    enforce_response={"cap_exceeded": False},
    failure_message="WB temporary failure",
)
CAH_EPOCH_PARTIAL_SYNC_001: Final[WbSyncContractCase] = WbSyncContractCase(
    case_id="CAH-EPOCH-PARTIAL-SYNC-001",
    keywords=("alpha", "beta"),
    expected_allowed_snapshot=("alpha", "beta"),
    enforce_response={"cap_exceeded": False},
    failure_message="WB temporary failure",
)
CAH_EPOCH_FACT_DRIFT_001: Final[EpochDriftContractCase] = EpochDriftContractCase(
    case_id="CAH-EPOCH-FACT-DRIFT-001",
    factual_position=18.0,
    confirmed_target_place=7,
)

CAH_LIFECYCLE_POSITIVE_001: Final[str] = "CAH-LIFECYCLE-POSITIVE-001"
CAH_LIFECYCLE_RETRY_001: Final[str] = "CAH-LIFECYCLE-RETRY-001"
CAH_LIFECYCLE_CONTRACT: Final[LifecycleContractCase] = LifecycleContractCase(
    case_id=CAH_LIFECYCLE_POSITIVE_001,
    retry_case_id=CAH_LIFECYCLE_RETRY_001,
    redis_enter_events=("enter",),
    minimum_telegram_notifications=2,
    wb_sync_calls=1,
)

ALL_CONTRACT_CASE_IDS: Final[frozenset[str]] = frozenset(
    {
        CAH_OWN_ASSOCIATED_001.case_id,
        CAH_OWN_FOREIGN_CONFIRM_001.case_id,
        CAH_OWN_FOREIGN_DISABLE_001.case_id,
        CAH_OWN_UNRELATED_WRITERS_001.case_id,
        *(case.case_id for case in FACTUAL_POSITION_CASES),
        CAH_EPOCH_RETRY_001.case_id,
        CAH_EPOCH_PARTIAL_SYNC_001.case_id,
        CAH_EPOCH_FACT_DRIFT_001.case_id,
        CAH_LIFECYCLE_POSITIVE_001,
        CAH_LIFECYCLE_RETRY_001,
    }
)
