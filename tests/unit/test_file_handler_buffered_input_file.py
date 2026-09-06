"""Regression: BufferedInputFile must not hit str.startswith in file_handler.

Protects AdvKeywordsSetting / get_telegram_image path where callers already
pass BufferedInputFile (typed on get_telegram_image) but _get_telegram_file
calls image_path.startswith without an InputFile guard.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from aiogram.types import BufferedInputFile

from app.file_handler import _get_telegram_file, get_telegram_image


@pytest.mark.asyncio
async def test_get_telegram_image_accepts_buffered_input_file_without_startswith() -> None:
    """BufferedInputFile must pass through (or return InputFile), not AttributeError.

    Current bug: _get_telegram_file calls image_path.startswith("http") on a
    BufferedInputFile → AttributeError: object has no attribute 'startswith'.
    """
    buffered = BufferedInputFile(b"\x89PNG\r\n\x1a\nfake", filename="wbgram.png")
    bot = MagicMock()

    result = await get_telegram_image(buffered, bot)

    assert isinstance(result, (BufferedInputFile, str))
    if isinstance(result, BufferedInputFile):
        assert result.filename == "wbgram.png"


@pytest.mark.asyncio
async def test_get_telegram_file_accepts_buffered_input_file_without_startswith() -> None:
    """Direct _get_telegram_file must not call startswith on BufferedInputFile."""
    buffered = BufferedInputFile(b"\x89PNG\r\n\x1a\nfake", filename="wbgram.png")
    bot = MagicMock()

    result = await _get_telegram_file(buffered, bot)  # type: ignore[arg-type]

    assert isinstance(result, (BufferedInputFile, str, int))
    if isinstance(result, BufferedInputFile):
        assert result.filename == "wbgram.png"
