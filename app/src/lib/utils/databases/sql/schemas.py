# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
# pylint: disable=E1136

"""Shared pydantic model classes."""

from typing import Optional, Union

from pydantic import BaseModel

possible_price_metrics = ["o", "h", "l", "c", "oc2", "hl2", "hlc3", "ohlc4"]

# possible_price_metrics means:

# "o"     = "Open"
# "h"     = "High"
# "l"     = "Low"
# "c"     = "Close"
# "oc2"   = ("Open" + "Close")/2
# "hl2"   = ("High" + "Low")/2
# "hlc3"  = ("High" + "Low" + "Close")/3
# "ohlc4" = ("Open" + "High" + "Low" + "Close")/4

# DateTimeType below could be:
#  - integer or string timestamp, measured in seconds or
#  - human readable datetime, 'YYYY-MM-DD HH:mm:ss' formated;
#    e.g. '2017-11-08 10:00:00'.

# For any of above cases, the value of timestamp - whose unit of
# measure is 'DateTimeType' - MUST be converted or originally measured
# in UTC time zone.

DateTimeType = Union[str, int]


class Market(BaseModel):
    """Market attributes"""

    broker_name: str
    quote_symbol: str
    base_symbol: str
    ticker_symbol: str


class Portfolio(BaseModel):
    """Market are formed by trading between 'quote' and 'base' assets,
    this class shows the quantity of each asset, given a certain
    Market; e.g., suppose, for the 'BTCUDST' binance market, that you
    have 100 USDTs and 0.02 BTC in your portfolio, so let's do

    p = portfolio (quote = 0.02, base = 100)

    ... that way:

    p.quote = 0.02
    p.base = 100

    Args:
        quote (float): Quote amount found on wallet
        base (float): Base amount found on wallet
    """

    quote: float = None
    base: float = None


class Quant(BaseModel):
    """Auxiliary class to store the amount quantity information, useful
    for the trade order flow"""

    is_enough: Optional[bool]
    value: Optional[str]


class Order(BaseModel):
    """Order parameters collection"""

    test_order: bool = False
    timestamp: Optional[int]
    id_by_broker: Optional[str]
    order_type: Optional[str]
    from_side: Optional[str]
    to_side: Optional[str]
    score: Optional[float]
    leverage: float = 1
    generated_signal: Optional[str]
    interpreted_signal: Optional[str]
    price: Optional[float]
    quantity: Optional[float]
    fulfilled: Optional[bool]
    fee: Optional[float]
    warnings: Optional[str]


class Classifier(BaseModel):
    """Classifier handler attributes"""

    name: str
    setup: BaseModel


class StopLoss(BaseModel):
    """Stoploss handler attributes"""

    is_on: bool
    name: str
    setup: BaseModel


class Broadcasters(BaseModel):
    """Stores the possible trading signals"""

    print_on_screen: str = "print_on_screen"
    telegram: str = "telegram"
    whatsapp: str = "whatsapp"
    email: str = "email"
    push: str = "push"


class ClassifierPayLoad(BaseModel):
    """Information that must be passed to get a classifier"""

    classifier: Classifier
    market: Market
    backtesting: bool
    result_length: int


class Treshold(BaseModel):
    """Fires the trigger when 'm_found' true conditions are found among
    the 'n_datapoints' values."""

    m_found: int
    n_datapoints: int


class Trigger(BaseModel):
    """Trigger parameters"""

    rate: float
    treshold: Treshold


class OperationalModes(BaseModel):
    """Stores the possible operation modes"""

    real_trading: str = "real_trading"
    test_trading: str = "test_trading"
    backtesting: str = "backtesting"


class Sides(BaseModel):
    """Stores the possible sides"""

    zeroed: str = "zeroed"
    long: str = "long"
    short: str = "short"


class Signals(BaseModel):
    """Stores the possible trading signals"""

    hold: str = "hold"
    buy: str = "buy"
    sell: str = "sell"
    naked_sell: str = "naked_sell"
    double_naked_sell: str = "double_naked_sell"
    double_buy: str = "double_buy"
    long_stopped: str = "long_stopped"
    short_stopped: str = "short_stopped"

    def get_all(self):
        return [signal for signal in list(self)]
