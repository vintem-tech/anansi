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
    weight_case_partial_opened:float = 1.0 # Recommended 0.0 or 1.0
    time_frame: str = "6h"

class OperationSetup(BaseModel):
    """Operational schema, with default values."""

    debbug: bool = True
    broadcasters: List[str] = ["PrintNotifier"]
    classifier_name: str = "DidiClassifier"
    classifier_setup: BaseModel = DidiClassifierSetup()
    market: Market = Market(
        broker_name="Binance", quote_symbol="BTC", base_symbol="USDT", ticker_symbol="BTCUSDT"
    )
    backtesting: bool = True
    initial_base_amount: float = 1000.00
    test_order: bool = False
    order_type: str = "market"
    stop_is_on: bool = False
    allow_naked_sells: bool = False

class Order(BaseModel):
    """Order parameters collection"""

    test_order: bool
    ticker_symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    notify: bool = True
