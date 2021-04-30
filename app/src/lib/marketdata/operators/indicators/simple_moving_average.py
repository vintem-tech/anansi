#from .base import price_columns

class SimpleMovingAverage:
    __slots__ = ["_klines"]

    def __init__(self, klines):
        self._klines = klines

    def apply(self, setup):
        self._klines.apply_indicator.trend.price_from_kline(
            price_metrics=setup.price_metrics
        )
        indicator_column = "SMA_{}".format(setup.number_samples)

        price_column = getattr(
            self._klines, "Price_{}".format(setup.price_metrics)
        )
        self._klines.loc[:, indicator_column] = price_column.rolling(
            window=setup.number_samples
        ).mean()
