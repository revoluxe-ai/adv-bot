"""Backfill флага автообновления минус-фраз через migration Job.

Модуль принадлежит migration layer и получает уже открытое write-соединение
от родительского Job orchestration. Он не используется application runtime.

Контракт: классификатор ``bot_active`` применяется **только к NULL**
(``NULL ∧ bot_active`` → true, иначе false). Уже проставленные значения
(в т.ч. UI-тогглы) не переписываются. Job можно гонять сколько угодно:
есть NULL — дозаполнит; NULL нет — UPDATE no-op. После успешного прогона
колонка усиливается до DEFAULT false + NOT NULL.

Долгосрочно надёжнее запретить NULL в проде (NOT NULL) и убрать этот
Job/миграционный backfill-path; до тех пор ``MIGRATION_BACKFILL_KIND`` —
явный controlled write-path для legacy NULL.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection

BACKFILL_KIND = "auto_update_minus_phrases_v1"


@dataclass(frozen=True)
class BackfillPreview:
    """Снимок строк до backfill и ожидаемое распределение NULL-классификатора."""

    total_records: int
    null_records: int
    active_records: int
    inactive_records: int
    expected_enabled_records: int
    expected_disabled_records: int


@dataclass(frozen=True)
class BackfillResult:
    """Результат preview, idempotent NULL-only update и финальной проверки."""

    preview: BackfillPreview
    updated_records: int
    incompatible_records: int


def preview_auto_update_minus_phrases(
    connection: Connection,
) -> BackfillPreview:
    """Считает затрагиваемые ``advsetting`` до изменения данных.

    ``expected_enabled/disabled`` — только среди текущих NULL (что Job
    реально изменит), не по всей таблице.

    Args:
        connection: Открытое write-соединение migration Job.

    Returns:
        Распределение legacy-записей и ожидаемые значения после classifier.

    Raises:
        sqlalchemy.exc.DBAPIError: Если таблица или колонки недоступны.
    """
    row = connection.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_records,
                COUNT(*) FILTER (
                    WHERE auto_update_minus_phrases IS NULL
                ) AS null_records,
                COUNT(*) FILTER (WHERE bot_active IS TRUE) AS active_records,
                COUNT(*) FILTER (WHERE bot_active IS NOT TRUE) AS inactive_records,
                COUNT(*) FILTER (
                    WHERE auto_update_minus_phrases IS NULL
                      AND bot_active IS TRUE
                ) AS expected_enabled_records,
                COUNT(*) FILTER (
                    WHERE auto_update_minus_phrases IS NULL
                      AND bot_active IS NOT TRUE
                ) AS expected_disabled_records
            FROM advsetting
            """
        )
    ).mappings().one()
    return BackfillPreview(
        total_records=int(row["total_records"]),
        null_records=int(row["null_records"]),
        active_records=int(row["active_records"]),
        inactive_records=int(row["inactive_records"]),
        expected_enabled_records=int(row["expected_enabled_records"]),
        expected_disabled_records=int(row["expected_disabled_records"]),
    )


def apply_auto_update_minus_phrases_backfill(
    connection: Connection,
) -> BackfillResult:
    """Заполняет только NULL по ``bot_active`` и завершает NOT NULL transition.

    Повторный запуск безопасен: UPDATE трогает лишь ``IS NULL``; уже
    выставленные true/false (включая ручные UI-тогглы) сохраняются.
    Финальный gate — отсутствие оставшихся NULL, не drift к ``bot_active``.

    Args:
        connection: Открытое write-соединение migration Job.

    Returns:
        Preview, число реально изменённых строк и остаток NULL.

    Raises:
        sqlalchemy.exc.DBAPIError: При ошибке update или schema transition.
    """
    preview = preview_auto_update_minus_phrases(connection)
    updated = connection.execute(
        text(
            """
            UPDATE advsetting
            SET auto_update_minus_phrases = (bot_active IS TRUE)
            WHERE auto_update_minus_phrases IS NULL
            """
        )
    )
    connection.execute(
        text(
            """
            ALTER TABLE advsetting
            ALTER COLUMN auto_update_minus_phrases SET DEFAULT false
            """
        )
    )
    connection.execute(
        text(
            """
            ALTER TABLE advsetting
            ALTER COLUMN auto_update_minus_phrases SET NOT NULL
            """
        )
    )
    remaining = connection.execute(
        text(
            """
            SELECT COUNT(*) AS incompatible_records
            FROM advsetting
            WHERE auto_update_minus_phrases IS NULL
            """
        )
    ).scalar_one()
    return BackfillResult(
        preview=preview,
        updated_records=int(getattr(updated, "rowcount", 0) or 0),
        incompatible_records=int(remaining),
    )
