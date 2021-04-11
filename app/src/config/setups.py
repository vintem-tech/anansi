"""User customizable parameters, like indicators, classifiers,
stoploss or even entire operations setups"""

# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods

from typing import List, Optional, Sequence, Union

from pydantic import BaseModel, validator

from ..lib.utils.databases.sql.schemas import (
    Broadcasters,
    Classifier,
    Market,
    StopLoss,
    possible_price_metrics,
)

DateTimeType = Union[str, int]
broadcasters = Broadcasters()


class SimpleMovingAverage(BaseModel):
    """Setup of 'simple_moving_average' trend indicator"""

    price_metrics: str = "ohlc4"
    number_samples: int = 7


class BollingerBands(BaseModel):
    """Setup of Bollinger bands volatility indicator"""

    price_metrics: str = "ohlc4"
    number_samples: int = 20
    number_STDs: float = 2.0


class DidiIndex(BaseModel):
    """ Setup of Didi index trend indicator"""

    price_metrics: str = "ohlc4"
    number_samples: Sequence[int] = (3, 8, 20)

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

        all_positives = all(x > 0 for x in value)
        ascending_order = bool(value[2] > value[1] > value[0])
        correct_length = bool(len(value) == 3)

        if not all_positives:
            raise ValueError("Number samples must be positive integers.")

        if not ascending_order:
            raise ValueError("Should be in ascending order.")

        if not correct_length:
            raise ValueError("Expected exactly 3 integer values.")
        return value


class DidiClassifier(BaseModel):
    """Setup of DidiClassifier operator, which uses didi index and
    bollinger bands indicators to proceed classification"""

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
    # e.g. "1m", "5m", "2h" ...
    debug_message_every: str = "6h"


class StopTrailing3T(BaseModel):
    """Triple Trigger Treshold Stop Trailing setup"""

    classifier_time_frame: str = "6h"
    price_metric: str = "oc2"


class BinanceMonitoring:
    """Binance monitored markets"""

    bases: list = ["USDT", "BTC"]
    quotes: list = [
        "BTC",
        "ETH",
        "NEO",
        "LINK",
        "EOS",
        "LTC",
        "XRP",
        "BNB",
        "ADA",
        "TRX",
    ]

    def markets(self) -> List[Market]:
        """Returns a list of binance markets to monitoring"""

        return [
            Market(
                broker_name="binance",
                quote_symbol=quote,
                base_symbol=base,
                ticker_symbol="{}{}".format(quote, base),
            )
            for base in self.bases
            for quote in self.quotes
            if quote != base
        ]


class Trading(BaseModel):
    """Trading setup schema, with default values."""

    score_that_triggers_long_side: float = 0.3  # <=1.0
    score_that_triggers_short_side: float = -0.3  # >=-1.0
    default_order_type: str = "market"
    allow_naked_sells: bool = False
    leverage = 1.0


class OperationalSetup(BaseModel):
    """Operation setup schema, with default values."""

    classifier: Classifier = DidiClassifier()
    stoploss: StopLoss = StopTrailing3T()
    trading: Trading = Trading()
    notifier = Notifier()
    backtesting: Optional[BackTesting] = BackTesting()
