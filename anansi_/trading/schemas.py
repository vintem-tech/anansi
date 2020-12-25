# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods

"""Specific trading pydantic model classes. For setups below, use the follow
price metrics:

"o"     = "Open"
"h"     = "High"
"l"     = "Low"
"c"     = "Close"
"oh2"   = ("Open" + "High")/2
"olc3"  = ("Open" + "Low" + "Close")/3
"ohlc4" = ("Open" + "High" + "Low" + "Close")/4
"""

from typing import Sequence, Optional
from pydantic import BaseModel, validator
from ..share.schemas import Market, TimeRange

possible_price_metrics = ["o", "h", "l", "c", "oh2", "olc3", "ohlc4"]


class SmaTripleCross(BaseModel):
    """ Setup of Cross Triple Simple Moving Average """

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


class BollingerBands(BaseModel):
    """Bollinger bands setup schema, with default values."""

    price_metrics: str = "ohlc4"
    number_samples: int = 20
    number_STDs: int = 2


class DidiIndex(BaseModel):
    """'Didi Index' ('agulhadas do Didi') setup schema, with default values."""

    allow_naked_sells: bool = False
    sma_triple_cross: SmaTripleCross = SmaTripleCross()
    bollinger_bands: BollingerBands = BollingerBands()


class Operation(BaseModel):
    """Operational schema, with default values."""

    classifier_name: str = "DidiIndex"
    classifier_setup: BaseModel = DidiIndex()
    market: Market = Market(
        broker_name="Binance", quote_symbol="BTC", base_symbol="USDT"
    )
    time_frame: str = "2h"
    backtesting: bool = True
    backtesting_range: Optional[TimeRange]
    initial_base_amount: float = 1000.00

    @property
    def classifier_payload(self) -> dict:
        """Prepares the payload for the classifier.

        Returns:
            [dict]: Classifier arguments.
        """
        return dict(
            classifier_name=self.classifier_name,
            market=self.market,
            time_frame=self.time_frame,
            setup=self.classifier_setup,
            backtesting=self.backtesting,
        )
