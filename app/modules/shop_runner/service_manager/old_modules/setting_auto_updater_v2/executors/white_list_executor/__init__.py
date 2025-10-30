"""Исполнители для управления белым списком ключевых слов."""

from .white_list_add_executor import WhiteListAddExecutor
from .white_list_remove_executor import WhiteListRemoveExecutor

__all__ = ["WhiteListAddExecutor", "WhiteListRemoveExecutor"]

