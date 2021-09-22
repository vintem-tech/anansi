# pylint: disable=too-few-public-methods

""" Price of an asset, from it's kline. Below, the possible values
​​for the 'price_metrics' parameter and the associated calculation.

"o"     = "Open"
"h"     = "High"
"l"     = "Low"
"c"     = "Close"
"oc2"   = ("Open" + "Close")/2
"hl2"   = ("High" + "Low")/2
"hlc3"  = ("High" + "Low" + "Close")/3
"ohlc4" = ("Open" + "High" + "Low" + "Close")/4
"""

columns = {
    "o": ["Open"],
    "h": ["High"],
    "l": ["Low"],
    "c": ["Close"],
    "oc2": ["Open", "Close"],
    "hl2": ["High", "Low"],
    "hlc3": ["High", "Low", "Close"],
    "ohlc4": ["Open", "High", "Low", "Close"],
}


class PriceFromKline:
    """Price of an asset, from it's kline."""

    __slots__ = ["_klines"]

    def __init__(self, klines):
        self._klines = klines

    def apply(self, price_metrics="ohlc4") -> None:
        """Calculation of the price, per se, from an average of the
        values ​​of the indicated columns

        :param price_metrics: Desired metrics for price calculation,
                              defaults to "ohlc4"
        :type price_metrics: str, optional
        :raises AttributeError: Unlisted 'price_metrics'
        """

        price_keys = list(columns.keys())
        except_msg = "price_metrics should be in {}".format(price_keys)

        if price_metrics in price_keys:
            price_column = "Price_{}".format(price_metrics)
            columns_ = self._klines[columns[price_metrics]]
            self._klines.loc[:, price_column] = columns_.mean(axis=1)
            return

        raise AttributeError(except_msg)
