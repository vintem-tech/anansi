# pylint:disable=missing-module-docstring
# pylint:disable=missing-function-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods
# pylint:disable=no-name-in-module


from typing import List

from environs import Env
from pydantic import BaseModel

from ..utils.schemas import (
    Broadcasters,
    DateTimeType,
    Wallet,
)

initial_wallet: Wallet = dict(USDT=1000.00)  # Backtesting scenarios
broadcasters = Broadcasters()

env = Env()


class DefaultTimesettings(BaseModel):
    local_timezone = env.str("LOCAL_TIMEZONE", default="America/Bahia")
    system_timezone = env.str("SYSTEM_TIMEZONE", default="UTC")
    default_timestamp_unit = "s"
    human_readable_format = "YYYY-MM-DD HH:mm:ss"
    presented_in_human_readable_format = True


class BackTesting(BaseModel):
    """Backtesting attributes"""

    price_metrics: str = "ohlc4"
    start_datetime: DateTimeType = "2020-01-01 00:00:00"
    end_datetime: DateTimeType = "2021-03-14 00:00:00"


class Notifier(BaseModel):
    """Notifier handler attributes"""

    broadcasters: List = [broadcasters.print_on_screen, broadcasters.telegram]
    debug: bool = True
    debug_message_every: str = "6h"  # e.g. "1m", "5m", "2h" ...


class Trading(BaseModel):
    """Trading setup schema, with default values."""

    score_that_triggers_long_side: float = 0.3  # <=1.0
    score_that_triggers_short_side: float = -0.3  # >=-1.0
    default_order_type: str = "market"
    allow_naked_sells: bool = False
    leverage = 1.0


class Default(BaseModel):
    pass
