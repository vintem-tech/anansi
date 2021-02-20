# pylint: disable=E1136
import sys
from typing import Union
import telegram
from ...config.settings import system_settings

thismodule = sys.modules[__name__]
settings = system_settings()

class BaseNotifier:
    def debug(self, msg: str):
        raise NotImplementedError

    def error(self, msg: str):
        raise NotImplementedError

    def trade(self, msg: str):
        raise NotImplementedError


class TelegramNotifier(BaseNotifier):
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


class PrintNotifier(BaseNotifier):
    def __init__(self):
        super().__init__()

    def debug(self, msg: str):
        print(msg)

    def error(self, msg: str):
        print(msg)

    def trade(self, msg: str):
        print(msg)


class EmailNotifier(BaseNotifier):
    pass


class PushNotifier(BaseNotifier):
    pass

def get(
    broadcaster: str,
) -> Union[TelegramNotifier, PrintNotifier, EmailNotifier, PushNotifier]:
    return getattr(thismodule, broadcaster)()
