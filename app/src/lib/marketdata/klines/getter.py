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