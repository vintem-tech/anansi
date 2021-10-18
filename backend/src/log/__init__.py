from src.core.config import settings
from src.core.config.messages import NotifierHeader

from .broadcasters import get

header = NotifierHeader()


class Notifier:
    def __init__(self, operation):
        self.broadcasters = [
            get(broadcaster)
            for broadcaster in operation.setup().notifier.broadcasters
        ]

    def _spam(self, msg: str, method: str) -> None:
        _header = getattr(header, method)
        _msg = """{}{}""".format(_header, msg)
        for broadcaster in self.broadcasters:
            getattr(broadcaster, method)(_msg)

    def debug(self, msg: str) -> None:
        if settings.debug:
            self._spam(msg, method="debug")

    def error(self, msg: str):
        self._spam(msg, method="error")

    def trade(self, msg: str):
        self._spam(msg, method="trade")
