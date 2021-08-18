"""Bollinger Bands"""

# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods

from pydantic import BaseModel

class Setup(BaseModel):
    """Setup of Bollinger bands volatility indicator"""

    price_metrics: str = "ohlc4"
    number_samples: int = 20
    number_STDs: float = 2.0

class BollingerBands:

    __slots__ = ["_klines"]

    def __init__(self, klines):
        self._klines = klines

    def apply(self, setup:Setup=Setup()):
        self._klines.indicator.price.apply(price_metrics=setup.price_metrics)
        n_parameter = setup.number_samples
        k_parameter = setup.number_STDs

        price_column = getattr(
            self._klines, "Price_{}".format(setup.price_metrics)
        )
        sma = price_column.rolling(window=n_parameter).mean()
        deviation = price_column.rolling(window=n_parameter).std()

        upper_band = sma + k_parameter * deviation
        bottom_band = sma - k_parameter * deviation

        self._klines.loc[:, "Bollinger_SMA"] = sma
        self._klines.loc[:, "BB_upper"] = upper_band
        self._klines.loc[:, "BB_bottom"] = bottom_band
