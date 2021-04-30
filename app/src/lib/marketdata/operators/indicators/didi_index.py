"""Didi index (3 simple moving average with sauce)"""

# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods

from typing import Sequence  # List, Optional,

from pydantic import BaseModel, validator

from .....lib.utils.schemas import possible_price_metrics


class Setup(BaseModel):
    """ Setup of Didi index indicator"""

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


class DidiIndex:
    """Didi index (3 simple moving average with sauce)"""

    __slots__ = ["_klines"]

    def __init__(self, klines):
        self._klines = klines

    def apply(self, setup: Setup = Setup()):
        """didi_fast = SMA_fast/SMA_middle - 1
           didi_middle = SMA_middle/SMA_middle - 1 = 0.0
           didi_slow = SMA_slow/SMA_middle - 1

        :param setup: price_metrics and number_samples for each of 3 SMA
        :type setup: Setup, optional
        """

        self._klines.indicator.price.apply(price_metrics=setup.price_metrics)
        price_column = getattr(
            self._klines, "Price_{}".format(setup.price_metrics)
        )
        sma_series = list()

        for number in setup.number_samples:
            sma_series.append(price_column.rolling(window=number).mean())

        self._klines.loc[:, "Didi_fast"] = sma_series[0] / sma_series[1] - 1
        self._klines.loc[:, "Didi_middle"] = self._klines.apply(
            lambda row: 0.0, axis=1
        )
        self._klines.loc[:, "Didi_slow"] = sma_series[2] / sma_series[1] - 1
