# pylint: disable=too-few-public-methods

"""Deals specifically with klines, delivering them formatted as pandas
dataframes, with some extra methods, such as market indicators. This
module also acts as a queue for requesting klines from the brokers, in
order to do not exceed the their APIs limits. Finally, it also deals
with saving and reading klines to/from the 'time_series_storage'.
"""

import time

import pandas as pd

from ....lib.utils.schemas import Ticker
from ....lib.utils.tools.time_handlers import Now, time_frame_to_seconds
from ...brokers import get_broker
from .base import Getter


class GetterFromBroker(Getter):
    """Aims to serve as a queue for requesting klines (OHLC) through
    brokers endpoints, spliting the requests, in order to respect broker
    established limits. If a request limit is close to being reached,
    will pause the queue, until cooldown time pass. Returns sanitized
    klines to the client, formatted as pandas DataFrame."""

    __slots__ = [
        "_broker",
        "ticker_symbol",
        "minimum_time_frame",
        "_time_frame",
        "store_klines_round_by_round",
        "infinite_attempts",
        "_request_step",
    ]

    def __init__(self, ticker: Ticker, time_frame: str = str()):
        self._broker = get_broker(ticker.broker_name)
        self.ticker_symbol = ticker.ticker_symbol
        self.minimum_time_frame = self._broker.settings.possible_time_frames[0]
        self._time_frame = self._validate_tf(time_frame)
        super().__init__(ticker, self.time_frame)
        self.store_klines_round_by_round: bool = False
        self.infinite_attempts: bool = True
        self._request_step = self.__request_step()

    def _validate_tf(self, timeframe: str):
        tf_list = self._broker.settings.possible_time_frames
        if timeframe:
            if timeframe not in tf_list:
                raise ValueError("Time frame must be in {}".format(tf_list))
        else:
            timeframe = self.minimum_time_frame
        return timeframe

    @property
    def time_frame(self) -> str:
        """time frame str <amount><scale_unit> e.g. '1m', '2h'"""
        return self._time_frame

    @time_frame.setter
    def time_frame(self, time_frame_to_set):
        self._time_frame = self._validate_tf(time_frame_to_set)

    def oldest_open_time(self) -> int:
        return self._broker.oldest_kline(
            ticker_symbol=self.ticker_symbol, time_frame=self.time_frame
        ).Open_time.item()

    def newest_open_time(self) -> int:
        return Now().utc_timestamp()

    def __request_step(self) -> int:
        return (
            self._broker.settings.records_per_request
            * time_frame_to_seconds(self.time_frame)
        )

    def _get_core(self, since: int, until: int) -> pd.core.frame.DataFrame:
        klines = pd.DataFrame()
        for timestamp in range(since, until + 1, self._request_step):
            attempt = 0
            while True:
                try:
                    if self._broker.max_requests_limit_hit():
                        time.sleep(10)
                    else:
                        attempt += 1
                        _klines = self._broker.get_klines(
                            ticker_symbol=self.ticker_symbol,
                            time_frame=self._time_frame,
                            since=timestamp,
                        )
                        klines = klines.append(_klines, ignore_index=True)
                        if self.store_klines_round_by_round:
                            self.storage.append(_klines)
                        break

                except (BrokerError, StorageError) as err:
                    if self.infinite_attempts:
                        print("Fail, due the error: ", err)
                        time.sleep(cooldown_time(attempt))
                    else:
                        raise Exception.with_traceback(err) from err

        if self.ignore_unclosed_kline:
            klines = remove_last_kline_if_unclosed(klines, self.time_frame)
        return klines
