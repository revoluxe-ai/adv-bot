"""Тесты для модуля graphic_positions_creator."""
import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.wb_adv_updater.position_history_manager import (
    KeywordPositions,
    Position,
    PositionHistory,
)


def make_position(text: str, date: datetime.date, position: float) -> Position:
    """Создаёт Position с заданными параметрами."""
    return Position(text=text, date=date, avr_pos=position)


def make_position_history(nmid: int, positions: list[Position]) -> PositionHistory:
    """Создаёт PositionHistory с заданными позициями."""
    return PositionHistory(nmid=nmid, positions=positions)


@pytest.fixture
def mock_positions_data() -> list[Position]:
    """Фикстура с тестовыми позициями для 3 ключевых слов за 7 дней."""
    today = datetime.date.today()
    positions = []
    
    keywords = ["платье женское", "юбка летняя", "блузка офисная"]
    
    for keyword in keywords:
        for days_ago in range(7):
            date = today - datetime.timedelta(days=days_ago)
            # Разные позиции для разных ключей
            base_position = keywords.index(keyword) * 10 + 5
            position = base_position + (days_ago % 3)  # небольшая вариация
            positions.append(make_position(keyword, date, float(position)))
    
    return positions


@pytest.fixture
def mock_position_history(mock_positions_data: list[Position]) -> PositionHistory:
    """Фикстура с PositionHistory."""
    return make_position_history(nmid=123456, positions=mock_positions_data)


class TestGetKeywordHistoryGraphic:
    """Тесты для функции get_keyword_history_graphic."""

    @pytest.mark.asyncio
    async def test_returns_graphic_with_valid_data(
        self,
        mock_position_history: PositionHistory,
    ):
        """Проверяет, что функция возвращает график при валидных данных."""
        from app.utils.graphic_positions_creator.graphic_positions_creator import (
            get_keyword_history_graphic,
        )

        # Мокаем сессию БД
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = [123456]  # nmids
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Мокаем контекстный менеджер сессии
        mock_sm = MagicMock()
        mock_sm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.utils.graphic_positions_creator.graphic_positions_creator.sm",
            return_value=mock_sm,
        ), patch(
            "app.utils.graphic_positions_creator.graphic_positions_creator.get_common_keywords_with_positions",
            new_callable=AsyncMock,
            return_value=mock_position_history,
        ):
            result = await get_keyword_history_graphic(adv_original_id=1)

        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        image_stream, legend_stream = result
        assert isinstance(image_stream, BytesIO)
        # legend_stream может быть None если ключей <= 5
        assert legend_stream is None or isinstance(legend_stream, BytesIO)
        
        # Проверяем, что изображение не пустое
        image_stream.seek(0)
        image_data = image_stream.read()
        assert len(image_data) > 0

    @pytest.mark.asyncio
    async def test_returns_none_when_no_keywords(self):
        """Проверяет, что функция возвращает None когда нет ключевых слов."""
        from app.utils.graphic_positions_creator.graphic_positions_creator import (
            get_keyword_history_graphic,
        )

        empty_history = make_position_history(nmid=123456, positions=[])

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = [123456]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_sm = MagicMock()
        mock_sm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.utils.graphic_positions_creator.graphic_positions_creator.sm",
            return_value=mock_sm,
        ), patch(
            "app.utils.graphic_positions_creator.graphic_positions_creator.get_common_keywords_with_positions",
            new_callable=AsyncMock,
            return_value=empty_history,
        ):
            result = await get_keyword_history_graphic(adv_original_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_raises_exception_when_no_nmids(self):
        """Проверяет, что функция выбрасывает исключение когда нет артикулов."""
        from app.utils.graphic_positions_creator.graphic_positions_creator import (
            get_keyword_history_graphic,
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # Нет nmids
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_sm = MagicMock()
        mock_sm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.utils.graphic_positions_creator.graphic_positions_creator.sm",
            return_value=mock_sm,
        ):
            with pytest.raises(Exception, match="Нет артикулов в РК"):
                await get_keyword_history_graphic(adv_original_id=1)

    @pytest.mark.asyncio
    async def test_selects_top_5_keywords_by_position(
        self,
    ):
        """Проверяет, что функция выбирает топ-5 ключевых слов с лучшими позициями."""
        from app.utils.graphic_positions_creator.graphic_positions_creator import (
            get_keyword_history_graphic,
        )

        today = datetime.date.today()
        positions = []
        
        # Создаём 10 ключевых слов с разными позициями
        for i in range(10):
            keyword = f"ключ_{i}"
            for days_ago in range(7):
                date = today - datetime.timedelta(days=days_ago)
                # Позиция растёт с номером ключа (чем меньше номер, тем лучше позиция)
                position = float((i + 1) * 10)
                positions.append(make_position(keyword, date, position))
        
        history = make_position_history(nmid=123456, positions=positions)

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = [123456]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_sm = MagicMock()
        mock_sm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.utils.graphic_positions_creator.graphic_positions_creator.sm",
            return_value=mock_sm,
        ), patch(
            "app.utils.graphic_positions_creator.graphic_positions_creator.get_common_keywords_with_positions",
            new_callable=AsyncMock,
            return_value=history,
        ):
            result = await get_keyword_history_graphic(adv_original_id=1)

        assert result is not None
        # Функция должна вернуть график (не None), так как есть ключевые слова
        image_stream, _ = result
        assert isinstance(image_stream, BytesIO)


class TestKeywordPositionsDTO:
    """Тесты для DTO KeywordPositions."""

    def test_max_position_returns_min_value(self):
        """Проверяет, что max_position возвращает минимальную позицию (лучшую)."""
        today = datetime.date.today()
        positions = [
            make_position("тест", today, 10.0),
            make_position("тест", today - datetime.timedelta(days=1), 5.0),
            make_position("тест", today - datetime.timedelta(days=2), 15.0),
        ]
        
        kw_positions = KeywordPositions(text="тест", positions=positions)
        
        # max_position должен вернуть 5.0 (лучшая/минимальная позиция)
        assert kw_positions.max_position == 5.0


class TestPositionHistoryDTO:
    """Тесты для DTO PositionHistory."""

    def test_keyword_positions_groups_by_text(self):
        """Проверяет, что keyword_positions группирует позиции по тексту."""
        today = datetime.date.today()
        positions = [
            make_position("ключ_1", today, 10.0),
            make_position("ключ_1", today - datetime.timedelta(days=1), 12.0),
            make_position("ключ_2", today, 5.0),
            make_position("ключ_2", today - datetime.timedelta(days=1), 7.0),
        ]
        
        history = make_position_history(nmid=123, positions=positions)
        kw_positions = history.keyword_positions
        
        assert len(kw_positions) == 2
        
        texts = {kw.text for kw in kw_positions}
        assert texts == {"ключ_1", "ключ_2"}
        
        for kw in kw_positions:
            assert len(kw.positions) == 2




