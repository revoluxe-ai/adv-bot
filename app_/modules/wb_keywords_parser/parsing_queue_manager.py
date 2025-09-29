"""
Этот файл обеспечивает обратную совместимость со старыми импортами.
Перенаправляет на правильную реализацию в wb_parser/parsing_page_queue_manager.py
"""

from .wb_parser.parsing_page_queue_manager import ParsingQueueManager

# Для обратной совместимости
__all__ = ["ParsingQueueManager"]
