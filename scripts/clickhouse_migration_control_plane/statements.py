"""Нарезка statement корпуса после полнострочных комментариев ``--``.

Spec ``clickhouse-migration-lifecycle``: граница шага — один statement.
Комментарий не исполняется. Точка с запятой внутри строкового литерала
останавливает разбор до apply. Порт цели и координатор сюда не входят.
"""

from __future__ import annotations


class StatementParseError(Exception):
    """Разбор SQL остановился до нарезки statement.

    Spec ``clickhouse-migration-lifecycle``: точка с запятой в строке не
    даёт частичный список statement. ``code`` читает validate.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def split_statements(sql_text: str) -> tuple[str, ...]:
    """Вернуть statement после снятия полнострочных комментариев ``--``.

    Spec ``clickhouse-migration-lifecycle``: строка, у которой после
    пробелов стоит ``--``, не является statement, даже если в ней написано
    пересоздание объекта. Точка с запятой внутри одинарных кавычек
    останавливает разбор. Кавычка ``''`` и обратный слэш остаются экраном
    ClickHouse и сами по себе statement не режут.

    Args:
        sql_text: текст одного файла корпуса, включая комментарии.

    Returns:
        Непустые statement в порядке файла, вместе с завершающей ``;``.

    Raises:
        StatementParseError: код ``semicolon_in_string``.
    """
    active = _without_full_line_comments(sql_text)
    return _split_active_sql(active)


def _without_full_line_comments(sql_text: str) -> str:
    """Убрать строки, которые целиком являются комментарием ``--``.

    Хвостовой ``--`` на строке с SQL остаётся частью statement: spec снимает
    только полнострочные комментарии. Байты файла эта функция не пишет.
    """
    kept: list[str] = []
    for line in sql_text.splitlines(keepends=True):
        if line.lstrip().startswith("--"):
            continue
        kept.append(line)
    return "".join(kept)


def _split_active_sql(body: str) -> tuple[str, ...]:
    """Разрезать текст по ``;`` вне строкового литерала.

    Встреча ``;`` внутри кавычек не возвращает уже накопленный текст
    вызывающему: разбор поднимает ошибку сразу.
    """
    statements: list[str] = []
    buf: list[str] = []
    in_string = False
    index = 0
    length = len(body)
    while index < length:
        char = body[index]
        if in_string:
            if char == "\\" and index + 1 < length:
                buf.append(char)
                buf.append(body[index + 1])
                index += 2
                continue
            if char == "'":
                if index + 1 < length and body[index + 1] == "'":
                    buf.append("''")
                    index += 2
                    continue
                in_string = False
                buf.append(char)
                index += 1
                continue
            if char == ";":
                raise StatementParseError("semicolon_in_string")
            buf.append(char)
            index += 1
            continue
        if char == "'":
            in_string = True
            buf.append(char)
            index += 1
            continue
        if char == ";":
            buf.append(";")
            statement = "".join(buf).strip()
            if statement != "" and statement != ";":
                statements.append(statement)
            buf = []
            index += 1
            continue
        buf.append(char)
        index += 1
    tail = "".join(buf).strip()
    if tail != "":
        statements.append(tail)
    return tuple(statements)
