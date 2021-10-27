# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
# pylint: disable=unsubscriptable-object

from pydantic import BaseModel

class TelegramChatsIds(BaseModel):
    debug: int = 0
    error: int = 0
    trade: int = 0
