"""Чистая логика coverage-provenance: fail-closed, NO_DATA, пустые ряды."""

from __future__ import annotations

from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    FreshnessStatus,
    ReasonCode,
)


def is_interpreted_as_export_success(
    collection_outcome: CollectionOutcome,
    coverage: Coverage,
) -> bool:
    """
    Успех экспорта для потребителя: UNKNOWN не считается успехом (fail-closed).

    Returns:
        True только если оба измерения не UNKNOWN и coverage не FULL без оснований
        (FULL при UNKNOWN collection_outcome запрещён).
    """
    if collection_outcome == CollectionOutcome.UNKNOWN:
        return False
    if coverage == Coverage.UNKNOWN:
        return False
    return True


def assert_card_fail_closed(
    collection_outcome: CollectionOutcome,
    coverage: Coverage,
) -> None:
    """UNKNOWN не трактуется как успех или полное покрытие."""
    if collection_outcome == CollectionOutcome.UNKNOWN and coverage == Coverage.FULL:
        raise ValueError("UNKNOWN collection_outcome cannot pair with FULL coverage")
    if coverage == Coverage.UNKNOWN and collection_outcome == CollectionOutcome.SUCCESS:
        raise ValueError("UNKNOWN coverage cannot pair with SUCCESS collection_outcome")


def validate_independent_dimensions(
    collection_outcome: CollectionOutcome,
    coverage: Coverage,
    reason_codes: list[ReasonCode],
    freshness: FreshnessStatus,
) -> None:
    """
    Базовые инварианты независимости измерений.

    Raises:
        ValueError: при нарушении fail-closed или подмены freshness→coverage.
    """
    assert_card_fail_closed(collection_outcome, coverage)
    if freshness == FreshnessStatus.FRESH and coverage == Coverage.UNKNOWN:
        raise ValueError("freshness FRESH must not mask UNKNOWN coverage")


def reason_codes_for_campaign_physical_legs(
    *,
    scoped_adv_ids: list[int],
    observed_adv_ids: list[int],
    row_count: int,
) -> list[ReasonCode]:
    """
    Коды покрытия физических Auto/Search ног campaign stat.

    Пустой срез — ``NO_DATA`` (fail-closed), без нулевых строк. Непустое
    наблюдение строго меньшего множества ожидаемых id — ``PARTIAL_COLLECTION``.
    Полное наблюдение ожидаемых id не добавляет код само по себе.

    Args:
        scoped_adv_ids: Ожидаемые физические adv_id из PG scope.
        observed_adv_ids: campaign_id, реально присутствующие в срезе.
        row_count: Число строк payload (ноль ⇒ данных нет).

    Returns:
        Список reason codes для карточки campaign stat.
    """
    if row_count == 0:
        return [ReasonCode.NO_DATA]
    expected = set(scoped_adv_ids)
    observed = set(observed_adv_ids) & expected
    if not observed or expected - observed:
        return [ReasonCode.PARTIAL_COLLECTION]
    return []


def coverage_for_empty_campaign_stat(
    *,
    scoped_adv_ids: list[int],
    row_count: int,
    reason_codes: list[ReasonCode],
) -> Coverage:
    """
    Пустой CH-срез не доказывает FULL coverage.

    ``NO_DATA`` в reason_codes сам по себе не переводит coverage в PARTIAL.
    """
    if row_count > 0:
        return Coverage.PARTIAL
    if ReasonCode.NO_DATA in reason_codes and len(reason_codes) == 1:
        return Coverage.UNKNOWN
    if not scoped_adv_ids:
        return Coverage.NONE
    return Coverage.UNKNOWN


def apply_no_data_to_coverage(
    coverage: Coverage,
    reason_codes: list[ReasonCode],
) -> Coverage:
    """
    ``NO_DATA`` MUST NOT автоматически означать неполное coverage.

    Возвращает coverage без изменений, если единственный код — NO_DATA.
    """
    if reason_codes == [ReasonCode.NO_DATA]:
        return coverage
    return coverage
