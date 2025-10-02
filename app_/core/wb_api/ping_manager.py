from .base import BaseAPI
from .mixins.ping import WBAdvPingMixin


class PingManager(BaseAPI, WBAdvPingMixin):
    pass
