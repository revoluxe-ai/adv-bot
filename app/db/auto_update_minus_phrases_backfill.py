"""Одноразовый backfill флага автообновления минус-фраз через migration Job.

Модуль принадлежит migration layer и получает уже открытое write-соединение
от родительского Job orchestration. Он не используется application runtime:
legacy-строки классифицируются по ``bot_active``, preview и итоговая проверка
выполняются в том же контролируемом write-path.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection

BACKFILL_KIND = "auto_update_minus_phrases_v1"


@dataclass(frozen=True)
class BackfillPreview:
    """Снимок строк до backfill и ожидаемое распределение результата."""

    total_records: int
    null_records: int
    active_records: int
    inactive_records: int
    expected_enabled_records: int
    expected_disabled_records: int


@dataclass(frozen=True)
class BackfillResult:
    """Результат preview, idempotent update и финальной проверки."""

    preview: BackfillPreview
    updated_records: int
    incompatible_records: int


def preview_auto_update_minus_phrases(
    connection: Connection,
) -> BackfillPreview:
    """Считает затрагиваемые ``advsetting`` до изменения данных.

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
                COUNT(*) FILTER (WHERE bot_active IS NOT TRUE) AS inactive_records
            FROM advsetting
            """
        )
    ).mappings().one()
    active_records = int(row["active_records"])
    inactive_records = int(row["inactive_records"])
    return BackfillPreview(
        total_records=int(row["total_records"]),
        null_records=int(row["null_records"]),
        active_records=active_records,
        inactive_records=inactive_records,
        expected_enabled_records=active_records,
        expected_disabled_records=inactive_records,
    )


def apply_auto_update_minus_phrases_backfill(
    connection: Connection,
) -> BackfillResult:
    """Применяет classifier и завершает nullable-to-NOT-NULL transition.

    Повторный запуск безопасен: ``IS DISTINCT FROM`` обновляет только строки,
    чьё значение не совпадает с ``bot_active IS TRUE``. После update constraint
    усиливается только если несовместимых NULL больше нет.

    Args:
        connection: Открытое write-соединение migration Job.

    Returns:
        Preview, число реально изменённых строк и остаток несовместимых строк.

    Raises:
        sqlalchemy.exc.DBAPIError: При ошибке update или schema transition.
    """
    preview = preview_auto_update_minus_phrases(connection)
    updated = connection.execute(
        text(
            """
            UPDATE advsetting
            SET auto_update_minus_phrases = (bot_active IS TRUE)
            WHERE auto_update_minus_phrases IS DISTINCT FROM (bot_active IS TRUE)
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
               OR auto_update_minus_phrases IS DISTINCT FROM (bot_active IS TRUE)
            """
        )
    ).scalar_one()
    return BackfillResult(
        preview=preview,
        updated_records=int(getattr(updated, "rowcount", 0) or 0),
        incompatible_records=int(remaining),
    )
