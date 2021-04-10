# pylint: disable=E1136
import sys

import telegram

from ..config.settings import system_settings
from ..lib.tools.formatting import ConvertString

thismodule = sys.modules[__name__]
settings = system_settings()


class Base:
    def debug(self, msg: str):
        raise NotImplementedError

    def error(self, msg: str):
        raise NotImplementedError

    def trade(self, msg: str):
        raise NotImplementedError


class Telegram(Base):
    def __init__(self):
        super().__init__()
        self.settings = settings.telegram
        self.bot = telegram.Bot(self.settings.token)

    def debug(self, msg: str):
        self.bot.send_message(chat_id=self.settings.debug_id, text=msg)

    def error(self, msg: str):
        self.bot.send_message(chat_id=self.settings.error_id, text=msg)

    def trade(self, msg: str):
        self.bot.send_message(chat_id=self.settings.trade_id, text=msg)


class PrintOnScreen(Base):
    def debug(self, msg: str):
        print(msg)

    def error(self, msg: str):
        print(msg)

    def trade(self, msg: str):
        print(msg)


class Whatsapp(Base):
    pass


class Email(Base):
    pass


class Push(Base):
    pass


def get(broadcaster: str) -> Base:
    _broadcaster = ConvertString(broadcaster).from_snake_to_pascal()
    return getattr(thismodule, _broadcaster)()
