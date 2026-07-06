"""Regression tests for side-effect-free imports of user message sender package."""

from __future__ import annotations

import importlib
import logging
import sys


def test_user_message_sender_package_import_does_not_mutate_root_handlers() -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    sentinel_handler = logging.NullHandler()
    try:
        root_logger.handlers[:] = [sentinel_handler]
        sys.modules.pop("app.modules.user_message_sender", None)
        sys.modules.pop(
            "app.modules.user_message_sender.message_for_not_pay_user_sender",
            None,
        )

        importlib.import_module("app.modules.user_message_sender")

        assert root_logger.handlers == [sentinel_handler]
        assert (
            "app.modules.user_message_sender.message_for_not_pay_user_sender"
            not in sys.modules
        )
    finally:
        root_logger.handlers[:] = original_handlers
