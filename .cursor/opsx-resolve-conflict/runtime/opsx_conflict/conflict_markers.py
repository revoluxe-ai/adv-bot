"""Структурная детекция неразрешённых Git merge conflict markers.

Отличает реальные conflict blocks (COL0 ``<<<<<<<`` / ``=======`` / ``>>>>>>>``)
от литералов в строках, regex, комментариях и тестовых фикстурах.
"""

from __future__ import annotations

import re

_MARKER_START_LINE = re.compile(r"^<{7}(?:\s.*)?$")
_MARKER_SEP_LINE = re.compile(r"^={7}\s*$")
_MARKER_END_LINE = re.compile(r"^>{7}(?:\s.*)?$")


def has_unresolved_merge_markers(text: str) -> bool:
    """``True``, если в тексте есть структурные Git conflict markers на COL0."""

    if not text:
        return False

    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if _MARKER_START_LINE.match(line):
            separator_index = index + 1
            while separator_index < len(lines):
                if _MARKER_SEP_LINE.match(lines[separator_index]):
                    break
                if (
                    _MARKER_START_LINE.match(lines[separator_index])
                    or _MARKER_END_LINE.match(lines[separator_index])
                ):
                    return True
                separator_index += 1
            if separator_index >= len(lines):
                return True

            end_index = separator_index + 1
            while end_index < len(lines):
                if _MARKER_END_LINE.match(lines[end_index]):
                    return True
                if (
                    _MARKER_START_LINE.match(lines[end_index])
                    or _MARKER_SEP_LINE.match(lines[end_index])
                ):
                    return True
                end_index += 1
            return True

        if _MARKER_SEP_LINE.match(line) or _MARKER_END_LINE.match(line):
            return True
        index += 1
    return False
