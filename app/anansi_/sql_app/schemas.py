# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
# pylint: disable=E1136

"""Shared pydantic parameters classes."""

from typing import Union, Sequence, Optional, List
from pydantic import BaseModel, validator

# DateTimeType below could be:
#  - integer or string timestamp, measured in seconds or
#  - human readable datetime, 'YYYY-MM-DD HH:mm:ss' formated;
#    e.g. '2017-11-08 10:00:00'.

# For any of above cases, the value of timestamp - whose unit of
# measure is 'DateTimeType' - MUST be converted or originally measured
# in UTC time zone.


DateTimeType = Union[str, int]


class Market(BaseModel):
    """ Market attributes """

    broker_name: str
    #quote_symbol: str
    #base_symbol: str
    ticker_symbol: str


# possible_price_metrics means:

# "o"     = "Open"
# "h"     = "High"
# "l"     = "Low"
# "c"     = "Close"
# "oc2"   = ("Open" + "Close")/2
# "hl2"   = ("High" + "Low")/2
# "hlc3"  = ("High" + "Low" + "Close")/3
# "ohlc4" = ("Open" + "High" + "Low" + "Close")/4


possible_price_metrics = ["o", "h", "l", "c", "oc2", "hl2", "hlc3", "ohlc4"]


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


class DidiIndexSetup(BaseModel):
    """ Setup of Didi index trend indicator """

    price_metrics: str = "ohlc4"
    number_samples: Sequence[int] = (3, 20, 80)

    @validator("price_metrics")
    @classmethod
    def prevent_invalid_price_metrics(cls, value: str) -> str:
        """Given a certain price_metrics value, checks if this value are in
        'possible_price_metrics'.

        Args:
            value (str): price_metrics

        Raises:
            ValueError: An error occurs if the passed price_metrics is not in {}

        Returns:
            str: price_metrics, if it is valid.
        """.format(
            possible_price_metrics
        )
        valid_value = bool(value in possible_price_metrics)
        if not valid_value:
            raise ValueError(
                "Price metrics should be in {}".format(possible_price_metrics)
            )
        return value

    @validator("number_samples")
    @classmethod
    def prevent_inconsistencies(cls, value: Sequence[int]) -> Sequence[int]:
        """Check the values in 'number_of_samples' set.

        Args:
            value (Sequence[int]): 'number_of_samples' - Set with the number
            of candles that must be computed to calculate each moving average.

        Raises:
            ValueError: Raises an error if any value in the set is negative, or
            ValueError: values are not on ascending order, or
            ValueError: 'number_of_samples' set are passed with no exactly 3
            elements.

        Returns:
            Sequence[int]: 'number_of_samples' set.
        """

        non_positive_values = bool(False in [bool(x > 0) for x in value])
        if non_positive_values:
            raise ValueError("Number samples must be positive integers.")

        ascending_order = bool((value[2] > value[1] and value[1] > value[0]))
        if not ascending_order:
            raise ValueError("Should be in ascending order.")

        correct_length = bool(len(value) == 3)
        if not correct_length:
            raise ValueError("Expected 3 integer values, no more, no less.")
        return value


class BollingerBandsSetup(BaseModel):
    """Bollinger bands setup schema, with default values."""

    price_metrics: str = "ohlc4"
    number_samples: int = 20
    number_STDs: float = 2.0


class DidiClassifierSetup(BaseModel):
    """'Default classifier schema, with default values."""

    didi_index: DidiIndexSetup = DidiIndexSetup()
    bollinger_bands: BollingerBandsSetup = BollingerBandsSetup()
    partial_opened_bands_weight: float = 1.0
    time_frame: str = "6h"



class Signals(BaseModel):
    """Stores the possible trading signals"""

    hold: str = "hold"
    buy:str = "buy"
    sell:str = "sell"
    naked_sell:str = "naked_sell"
    double_naked_sell:str = "double_naked_sell"
    double_buy:str = "double_buy"
    long_stopped:str = "long_stopped"
    short_stopped:str = "short_stopped"


class Order(BaseModel):
    """Order parameters collection"""

    order_id: Optional[Union[str,int]]
    test_order: Optional[bool] = False
    order_type: Optional[str]

    from_side: Optional[str]
    to_side: Optional[str]
    leverage: Optional[float]

    generated_signal = Optional[str]
    suggested_quantity: Optional[float]

    signal: Optional[str]
    price: Optional[float]
    timestamp: Optional[int]
    proceeded_quantity: Optional[float]

    filled: Optional[bool]
    fee: Optional[float]
    warnings: Optional[str]

class BackTesting(BaseModel):
    is_on: bool
    price_metrics: str = "ohlc4"
    fee_rate_decimal :float = 0.001
    initial_portfolio = Portfolio(quote=0.0, base=1000.00)

class Classifier(BaseModel):
    name: str
    setup: BaseModel

class StopLoss(BaseModel):
    is_on: bool
    name: str
    setup: BaseModel

class NotifierLevels: # Muito possivelmente desnecessário, já que serão atributos do notifier.
    debug: str = "debug"
    info: str = "info"
    warning: str = "warning"
    error: str  = "error"

class NotifierBroadcasters:
    default_print: str = "default_print"
    default_log:str = "default_log"
    telegram:str = "telegram"
    whatsapp:str = "whatsapp"
    email:str = "email"
    push:str = "push"


class Notifier:
    debug: bool
    broadcasters: List

class Treshold(BaseModel):
    """Given n measurements, fires the trigger when n positives are achieved"""

    n_measurements: int
    n_positives: int


class Trigger(BaseModel):
    """Trigger parameters"""

    rate: float
    treshold: Treshold


class StopTrailing3T(BaseModel):
    """Triple Trigger Treshold Stop Trailing setup"""

    time_frame = "5m"
    price_metric = "oc2"
    first_trigger = Trigger(
        rate=5, treshold=Treshold(n_measurements=6, n_positives=3)
    )
    second_trigger = Trigger(
        rate=3, treshold=Treshold(n_measurements=18, n_positives=12)
    )
    third_trigger = Trigger(
        rate=1, treshold=Treshold(n_measurements=36, n_positives=20)
    )
    update_target_if = Trigger(
        rate=0.7, treshold=Treshold(n_measurements=10, n_positives=7)
    )

class OperationalSetup(BaseModel):
    """Operational schema, with default values."""

    classifier: Classifier
    stoploss: StopLoss
    notifier: Notifier
    backtesting: Optional[BackTesting]

    market: Market
    default_order_type: str
    allow_naked_sells: bool
