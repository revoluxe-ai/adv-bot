__all__ = ["BaseWBApi", "mixins"]


def __getattr__(name: str):
    if name == "BaseWBApi":
        from .base_wb_api import BaseWBApi as _BaseWBApi
        return _BaseWBApi
    if name == "mixins":
        from . import mixins as _mixins
        return _mixins
    raise AttributeError(f"module 'app.core.mp.wb' has no attribute {name!r}")
