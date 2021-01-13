import sys
import telegram
from typing import Union, List
from .settings import TelegramSettings

thismodule = sys.modules[__name__]

class BaseNotifier:

    def debbug(self, msg:str):
        raise NotImplementedError
    
    def error(self, msg:str):
        raise NotImplementedError
    
    def trade(self, msg:str):
        raise  NotImplementedError

class TelegramNotifier(BaseNotifier):
    def __init__(self):
        super().__init__()
        self.settings=TelegramSettings()
        self.bot = telegram.Bot(self.settings.token)

    def debbug(self, msg:str):
        self.bot.send_message(chat_id=self.settings.debbug_id, text=msg)

    def error(self, msg:str):
        self.bot.send_message(chat_id=self.settings.erro_id, text=msg)

    
    def trade(self, msg:str):
        self.bot.send_message(chat_id=self.settings.trade_id, text=msg)


class PrintNotifier(BaseNotifier):
    def __init__(self):
        super(PrintNotifier, self).__init__()
    
    def debbug(self, msg:str):
        print(msg)

    def error(self, msg:str):
        print(msg)
    
    def trade(self, msg:str):
        print(msg)

class EmailNotifier(BaseNotifier):
    def __init__(self):
        super(EmailNotifier, self).__init__()


class PushNotifier(BaseNotifier):
    def __init__(self):
        super(PushNotifier, self).__init__()


class Notifier:
    def __init__(self, broadcasters: List[str]):
        self.broadcasters: List[
            Union[TelegramNotifier, PrintNotifier, EmailNotifier, PushNotifier]
        ] = [getattr(thismodule, broadcaster)() for broadcaster in broadcasters]

        self.show_header = True

    def debbug(self, msg: str) -> None:
        header = ""
        if self.show_header:
            header = """This is a debbug message. If you see this, debbug=True\n\n"""

        msg = """{}{}""".format(header, msg)

        for broadcaster in self.broadcasters:
            broadcaster.debbug(msg)

    def error(self, msg:str):
        header = ""
        if self.show_header:
            header = """An error occur. Details: \n\n"""

        msg = """{}{}""".format(header, msg)

        for broadcaster in self.broadcasters:
            broadcaster.error(msg)

    def trade(self, msg:str):
        header = ""
        if self.show_header:
            header = """Trade alert! Order details: \n\n"""

        msg = """{}{}""".format(header, msg)

        for broadcaster in self.broadcasters:
            broadcaster.trade(msg)


def get_notifier(broadcasters: List[str]) -> Notifier:
    return Notifier(broadcasters)
