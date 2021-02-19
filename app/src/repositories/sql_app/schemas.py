# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
# pylint: disable=E1136

"""Shared pydantic model classes."""

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
    quote_symbol: str
    base_symbol: str
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

    price_metrics: str
    number_samples: Sequence[int]

    @validator("price_metrics")
    @classmethod
    def prevent_invalid_price_metrics(cls, value: str) -> str:
        """Given a certain price_metrics value, checks if this value
        are in 'possible_price_metrics'.

        Args:
            value (str): price_metrics

        Raises:
            ValueError: An error occurs if the passed price_metrics is
            not in {}

        Returns:
            str: price_metrics, if it is valid.
        """.format(
            possible_price_metrics
        )

        if not value in possible_price_metrics:
            raise ValueError(
                "Price metrics should be in {}".format(possible_price_metrics)
            )
        return value

    @validator("number_samples")
    @classmethod
    def prevent_inconsistencies(cls, value: Sequence[int]) -> Sequence[int]:
        """Check the values in 'number_of_samples' set.

        Args:
            value (Sequence[int]): 'number_of_samples' - Set with the
            number of candles that must be computed to calculate each
            moving average.

        Raises:
            ValueError: Raises an error if any value in the set is
            negative, or values are not on ascending order, or set
            'number_of_samples' was passed with no exactly 3 elements.

        Returns:
            Sequence[int]: 'number_of_samples' set.
        """

        all_positives = all([x > 0 for x in value])
        ascending_order = bool(value[2] > value[1] > value[0])
        correct_length = bool(len(value) == 3)

        if not all_positives:
            raise ValueError("Number samples must be positive integers.")

        if not ascending_order:
            raise ValueError("Should be in ascending order.")

        if not correct_length:
            raise ValueError("Expected 3 integer values, no more, no less.")
        return value


class BollingerBandsSetup(BaseModel):
    """Bollinger bands setup schema, with default values."""

    price_metrics: str
    number_samples: int
    number_STDs: float


class DidiClassifierSetup(BaseModel):
    """'Default classifier schema, with default values."""

    didi_index: DidiIndexSetup
    bollinger_bands: BollingerBandsSetup
    partial_opened_bands_weight: float
    time_frame: str


class Order(BaseModel):
    """Order parameters collection"""

    timestamp: Optional[int]
    order_id: Optional[Union[str, int]]
    order_type: Optional[str]
    from_side: Optional[str]
    to_side: Optional[str]
    leverage: Optional[float]
    generated_signal: Optional[str]
    suggested_quantity: Optional[float]
    signal: Optional[str]
    price: Optional[float]
    test_order: bool = False
    proceeded_quantity: Optional[float]
    fulfilled: Optional[bool]
    fee: Optional[float]
    warnings: Optional[str]


class BackTesting(BaseModel):
    """Information about backtesting attributes"""
    is_on: bool
    price_metrics: str
    fee_rate_decimal: float
    initial_portfolio: Portfolio


class Classifier(BaseModel):
    """Information about classifier attributes"""
    name: str
    setup: BaseModel


class StopLoss(BaseModel):
    """Information about stoploss attributes"""
    is_on: bool
    name: str
    setup: BaseModel


class Notifier(BaseModel):
    """Information about notifier attributes"""
    debug: bool
    broadcasters: List


class Treshold(BaseModel):
    """Fires the trigger when 'm_found' true conditions are found among
    the 'n_datapoints' values."""

    m_found: int
    n_datapoints: int


class Trigger(BaseModel):
    """Trigger parameters"""

    rate: float
    treshold: Treshold


class StopTrailing3T(BaseModel):
    """Triple Trigger Treshold Stop Trailing setup"""

    time_frame:str
    price_metric:str
    
    
    
    # Acho que será desnecessário
    first_trigger: Trigger
    second_trigger: Trigger
    third_trigger: Trigger
    update_target_if: Trigger


class OperationalSetup(BaseModel):
    """Operational schema, with default values."""

    classifier: Classifier
    stoploss: StopLoss
    notifier: Notifier
    backtesting: Optional[BackTesting]

    market: Market
    default_order_type: str
    allow_naked_sells: bool


# Parameters collections
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


class Broadcasters(BaseModel):
    """Stores the possible trading signals"""

    print_on_screen: str = "print_on_screen"
    telegram: str = "telegram"
    whatsapp: str = "whatsapp"
    email: str = "email"
    push: str = "push"
