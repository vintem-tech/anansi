"""User customizable parameters, like indicators, classifiers,
stoploss or even entire operations setups"""

# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods
import sys
from typing import List, Optional, Sequence

from pydantic import BaseModel, validator

from ..lib.utils.schemas import (
    Broadcasters,
    Classifier,
    DateTimeType,
    StopLoss,
    Wallet,
    possible_price_metrics,
)

thismodule = sys.modules[__name__]

initial_wallet: Wallet = dict(USDT=1000.00) # Backtesting scenarios
broadcasters = Broadcasters()


class DidiClassifier(BaseModel):
    """Setup of DidiClassifier operator, which uses didi index and
    bollinger bands indicators to generate a classification score"""

    time_frame: str = "6h"
    didi_index = DidiIndex()
    bollinger_bands = BollingerBands()

    # Below values must be in range(0.0, 1.0) | 'bb' = 'Bollinger bands'
    weight_if_only_upper_bb_opened: float = 1.0
    weight_if_only_bottom_bb_opened: float = 1.0


class BackTesting(BaseModel):
    """Backtesting attributes"""

    price_metrics: str = "ohlc4"
    fee_rate_decimal: float = 0.001
    start_datetime: DateTimeType = "2020-01-01 00:00:00"
    end_datetime: DateTimeType = "2021-03-14 00:00:00"


class Notifier(BaseModel):
    """Notifier handler attributes"""

    broadcasters: List = [broadcasters.print_on_screen, broadcasters.telegram]
    debug: bool = True
    debug_message_every: str = "6h" # e.g. "1m", "5m", "2h" ...


class StopTrailing3T(BaseModel):
    """Triple Trigger Treshold Stop Trailing setup"""

    classifier_time_frame: str = "6h"
    price_metric: str = "oc2"


class Trading(BaseModel):
    """Trading setup schema, with default values."""

    score_that_triggers_long_side: float = 0.3  # <=1.0
    score_that_triggers_short_side: float = -0.3  # >=-1.0
    default_order_type: str = "market"
    allow_naked_sells: bool = False
    leverage = 1.0


class OperationalSetup(BaseModel):
    """Operation setup schema, with default values."""

    classifier =  Classifier(
        name = "DidiClassifier",
        setup = DidiClassifier()
    )
    stoploss: StopLoss = StopTrailing3T()
    trading: Trading = Trading()
    notifier = Notifier()
    backtesting: Optional[BackTesting] = BackTesting()


def get_setup(name: str):
    return getattr(thismodule, name)()
