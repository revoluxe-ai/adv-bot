class ShopRunnerCriticalError(Exception):
    """Base class for all ShopRunner exceptions."""

    pass


class FullAdvStatUpdateCriticalError(Exception):
    """Exception raised when full adv stat update fails."""

    pass


class CommonCoroutineError(Exception):
    pass
