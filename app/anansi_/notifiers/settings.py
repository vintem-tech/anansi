# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods

from environs import Env
from pydantic import BaseModel

env = Env()

class TelegramSettings(BaseModel):
    token:str = env.str("TELEGRAM_TOKEN", default=str())
    debbug_id:int = env.int("TELEGRAM_DEBBUG_ID", default=str())
    error_id:int = env.int("TELEGRAM_ERROR_ID", default=str())
    trade_id:int = env.int("TELEGRAM_TRADE_ID", default=str())