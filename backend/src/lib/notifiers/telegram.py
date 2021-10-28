from src.core.config import default_system_settings
from src.utils.schemas.notifiers import TelegramChatsIds
from src.log import logger
import telegram
from telegram import TelegramError


class Telegram:
    def __init__(
        self, chats_ids: TelegramChatsIds, token=default_system_settings.TELEGRAM_BOT_TOKEN
    ):
        self.bot = telegram.Bot(token)
        self.debug_id = chats_ids.debug
        self.error_id = chats_ids.error
        self.trade_id = chats_ids.trade

    def debug(self, msg: str):
        try:
            self.bot.send_message(chat_id=self.debug_id, text=msg)
        except (TelegramError, Exception) as error:
            logger.exception(error)

    def error(self, msg: str):
        try:
            self.bot.send_message(chat_id=self.error_id, text=msg)
        except (TelegramError, Exception) as error:
            logger.exception(error)
            self.debug(msg)

    def trade(self, msg: str):
        try:
            self.bot.send_message(chat_id=self.trade_id, text=msg)
        except (TelegramError, Exception) as error:
            logger.exception(error)
            self.debug(msg)
