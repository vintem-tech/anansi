"""Simple Moving Average"""

# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods

from pydantic import BaseModel

class Setup(BaseModel):
    """Setup of simple moving average indicator"""

    price_metrics: str = "ohlc4"
    number_samples: int = 7


class SimpleMovingAverage:
    """Calculates the average of a selected range of prices,
    by the number of periods (number_samples) in that range.
    """

    __slots__ = ["_klines"]

    def __init__(self, klines):
        self._klines = klines

    def apply(self, setup:Setup=Setup()):
        """SMA = (P1​ + P2 ​+ ... + Pn)/n

            ​where:
                Pn​ = the Price of an asset at period n
                n = the number of total periods​ (number_samples)

        :param setup: price_metrics and number_samples
        :type setup: Setup, optional
        """

        self._klines.indicator.price.apply(price_metrics=setup.price_metrics)
        indicator_column = "SMA_{}".format(setup.number_samples)

        price_column = getattr(
            self._klines, "Price_{}".format(setup.price_metrics)
        )
        self._klines.loc[:, indicator_column] = price_column.rolling(
            window=setup.number_samples
        ).mean()
