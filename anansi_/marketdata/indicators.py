""" All market indicators are coded here; some indicators are based on 
prices only, so the price are calculated from klines by 'price_from_kline'
method on 'Trend' indicators. For that, the desired 'price_metrics' must 
be passed, which, by default, is 'ohlc4'. Below, the possible values ​​for 
this parameter, as well as the associated calculation.

"o"     = "Open"
"h"     = "High"
"l"     = "Low"
"c"     = "Close"
"oh2"   = ("Open" + "High")/2
"olc3"  = ("Open" + "Low" + "Close")/3
"ohlc4" = ("Open" + "High" + "Low" + "Close")/4
"""

import pandas as pd

_columns = {
    "o": ["Open"],
    "h": ["High"],
    "l": ["Low"],
    "c": ["Close"],
    "hl2": ["High", "Low"],
    "hlc3": ["High", "Low", "Close"],
    "ohlc4": ["Open", "High", "Low", "Close"],
}


class Trend:
    __slots__ = ["_klines"]

    def __init__(self, klines):
        self._klines = klines

    def price_from_kline(self, price_metrics="ohlc4"):
        self._klines.loc[:, "Price"] = (
            self._klines[_columns[price_metrics]]
        ).mean(axis=1)

    def simple_moving_average(self, setup):
        self._klines.apply_indicator.trend.price_from_kline(price_metrics=setup.price_metrics)
        indicator_column = "SMA_{}".format(setup.number_samples)
        self._klines.loc[:, indicator_column] = self._klines.Price.rolling(
            window=setup.number_samples
        ).mean()


class Momentum:
    def __init__(self, klines):
        self._klines = klines


class Volatility:
    def __init__(self, klines):
        self._klines = klines
    
    def bollinger_bands(self, setup):
        self._klines.apply_indicator.trend.price_from_kline(price_metrics=setup.price_metrics)
        n = setup.number_samples
        k = setup.number_STDs

        sma = self._klines.Price.rolling(window=n).mean()
        deviation = self._klines.Price.rolling(window=n).std()
        upper_band = sma + k*deviation
        lower_band = sma - k*deviation

        self._klines.loc[:, "Bollinger_SMA"] = sma
        self._klines.loc[:, "BB_upper"] = upper_band
        self._klines.loc[:, "BB_lower"] = lower_band


class Volume:
    def __init__(self, klines):
        self._klines = klines
