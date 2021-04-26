from ...utils.schemas import Ticker

class Getter:
        __slots__ = [
        "ticker",
        "time_frame",
        "oldest_open_time",
        "storage",
        "return_as_human_readable",
        "ignore_unclosed_kline",
    ]

    def __init__(self, broker_name:str, ticker: Ticker, time_frame: str = str()):
        self.broker_name: broker_name
        self.ticker = ticker
        self.time_frame = time_frame

        self.oldest_open_time = self._oldest_open_time()
        self.return_as_human_readable = True
        self.ignore_unclosed_kline = True

@pd.api.extensions.register_dataframe_accessor("apply_indicator")
class ApplyIndicator:
    """Klines based market indicators, grouped by common scope."""

    def __init__(self, klines):
        self._klines = klines
        self.trend = indicators.Trend(self._klines)
        self.momentum = indicators.Momentum(self._klines)
        self.volatility = indicators.Volatility(self._klines)
        self.volume = indicators.Volume(self._klines)
