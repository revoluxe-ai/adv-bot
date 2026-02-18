"""Unit tests for get_name_for_adv (adv name template)."""

import pytest

from app.modules.adv_creator.backend.main_manager import get_name_for_adv


pytestmark = pytest.mark.unit


def test_complex_name_is_article_and_card_name_only() -> None:
    """Комплексная РК: шаблон «Артикул Название карточки» без Авто/Аукцион."""
    # артикул=100500, название карточки="Куртка зимняя" -> "100500 Куртка зимняя"
    assert get_name_for_adv(100500, "Куртка зимняя", "complex") == "100500 Куртка зимняя"
    assert get_name_for_adv(1, "Товар", "complex") == "1 Товар"


def test_auto_name_includes_type_word() -> None:
    """Авто РК: в имени есть слово Авто."""
    name = get_name_for_adv(100500, "Куртка зимняя", "auto")
    assert name == "100500 Авто Куртка зимняя"


def test_auction_name_includes_type_word() -> None:
    """Аукцион РК: в имени есть слово Аукцион."""
    name = get_name_for_adv(100500, "Куртка зимняя", "auction")
    assert name == "100500 Аукцион Куртка зимняя"


def test_complex_name_truncated_to_128() -> None:
    """Результат обрезается до 128 символов."""
    long_card = "A" * 200
    result = get_name_for_adv(123, long_card, "complex")
    assert len(result) == 128
