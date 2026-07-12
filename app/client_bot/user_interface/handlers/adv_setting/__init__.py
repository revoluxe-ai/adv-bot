"""Compatibility exports for the campaign settings handler package."""

from types import ModuleType
import sys

from . import adv_setting as _impl
from .adv_setting import *  # noqa: F401,F403
from .adv_setting import get_adv_setting
from .adv_setting import get_adv_setting_or_none
from .adv_setting import get_wb_user_cabinet
from .adv_setting import get_wb_user_cabinet_or_none
from .adv_setting import update_and_get_adv_setting


__all__ = ["get_adv_setting",
           "get_adv_setting_or_none",
           "get_wb_user_cabinet",
           "update_and_get_adv_setting",
           "get_wb_user_cabinet_or_none",
           ]


class _AdvSettingPackage(ModuleType):
    """Forward test patches on the package API to the implementation module."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name != "_impl" and hasattr(_impl, name):
            setattr(_impl, name, value)

    def __getattr__(self, name: str) -> object:
        try:
            return getattr(_impl, name)
        except AttributeError as exc:
            raise AttributeError(
                f"module {__name__!r} has no attribute {name!r}"
            ) from exc


sys.modules[__name__].__class__ = _AdvSettingPackage
